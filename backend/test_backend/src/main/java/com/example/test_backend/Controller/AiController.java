package com.example.test_backend.Controller;

import com.example.test_backend.Service.RecordsService;
import com.example.test_backend.Service.StatisticsService;
import com.example.test_backend.entity.Vo.CategoryStatisticsVO;
import com.example.test_backend.entity.Vo.MonthlyStatisticsVO;
import com.example.test_backend.entity.Vo.RecordVO;
import com.example.test_backend.interceptor.UserContext;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

/**
 * AI对话转发控制器
 * 将前端AI对话请求转发到 personal-ledger 的Express后端（端口3001）
 */
@Slf4j
@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class AiController {

    @Value("${ai.service.url:http://localhost:3001}")
    private String aiServiceUrl;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final StatisticsService statisticsService;
    private final RecordsService recordsService;

    /**
     * 创建新AI会话
     */
    @PostMapping("/sessions")
    public Map<String, Object> createSession(@RequestBody Map<String, String> body) {
        String title = body.getOrDefault("title", "新对话");
        try {
            URL url = new URL(aiServiceUrl + "/api/sessions");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setDoOutput(true);
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(10000);

            // 发送请求体
            String jsonBody = objectMapper.writeValueAsString(Map.of("title", title));
            try (OutputStream os = conn.getOutputStream()) {
                os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
            }

            int code = conn.getResponseCode();
            BufferedReader reader = new BufferedReader(new InputStreamReader(
                code == 200 ? conn.getInputStream() : conn.getErrorStream(), StandardCharsets.UTF_8));
            String response = reader.lines().collect(Collectors.joining());
            reader.close();

            Map<String, Object> result = objectMapper.readValue(response, Map.class);
            result.put("userId", UserContext.getUser()); // 附加userId
            return result;
        } catch (Exception e) {
            log.error("创建AI会话失败", e);
            return Map.of("error", "创建会话失败");
        }
    }

    /**
     * 获取所有会话
     */
    @GetMapping("/sessions")
    public Map<String, Object> getSessions() {
        try {
            URL url = new URL(aiServiceUrl + "/api/sessions");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(10000);

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
            String response = reader.lines().collect(Collectors.joining());
            reader.close();

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> sessions = objectMapper.readValue(response,
                new TypeReference<List<Map<String, Object>>>() {
                });
            // TODO: 后续可在Express端按userId过滤
            return Map.of("sessions", sessions);
        } catch (Exception e) {
            log.error("获取会话列表失败", e);
            return Map.of("sessions", Collections.emptyList());
        }
    }

    /**
     * 获取会话的消息
     */
    @GetMapping("/sessions/{id}/messages")
    public List<Map<String, Object>> getMessages(@PathVariable String id) {
        try {
            URL url = new URL(aiServiceUrl + "/api/sessions/" + id + "/messages");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(10000);

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
            String response = reader.lines().collect(Collectors.joining());
            reader.close();

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> messages = objectMapper.readValue(response,
                new TypeReference<List<Map<String, Object>>>() {
                });
            return messages;
        } catch (Exception e) {
            log.error("获取消息失败", e);
            return Collections.emptyList();
        }
    }

    /**
     * SSE流式对话（核心接口）
     * 直接管道转发Express后端的SSE流到前端
     */
    @GetMapping("/chat/stream")
    public void chatStream(
            @RequestParam String sessionId,
            @RequestParam String message,
            HttpServletResponse response) {
        try {
            response.setContentType("text/event-stream");
            response.setCharacterEncoding("UTF-8");
            response.setHeader("Cache-Control", "no-cache");
            response.setHeader("Connection", "keep-alive");
            response.setHeader("X-Accel-Buffering", "no"); // 禁用Nginx缓冲

            // 构建请求到Express后端
            String query = String.format("/api/chat/stream?sessionId=%s&message=%s",
                URLEncoder.encode(sessionId, StandardCharsets.UTF_8),
                URLEncoder.encode(message, StandardCharsets.UTF_8));
            URL url = new URL(aiServiceUrl + query);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(300000); // AI对话可能较长时间（5分钟）

            // 管道：Express的SSE响应 -> 写入HTTP响应
            try (InputStream in = conn.getInputStream();
                 OutputStream out = response.getOutputStream()) {

                byte[] buffer = new byte[4096];
                int bytesRead;
                while ((bytesRead = in.read(buffer)) != -1) {
                    out.write(buffer, 0, bytesRead);
                    out.flush();
                }
            }
        } catch (Exception e) {
            log.error("AI对话流转发失败", e);
            try {
                Map<String, Object> err = Map.of("type", "error", "error", "对话处理失败");
                String errorData = "data: " + objectMapper.writeValueAsString(err) + "\n\n";
                response.getOutputStream().write(errorData.getBytes(StandardCharsets.UTF_8));
                response.getOutputStream().flush();
            } catch (IOException ex) {
                log.error("写入错误响应失败", ex);
            }
        }
    }

    /**
     * 搜索FAQ知识库
     */
    @GetMapping("/faq/search")
    public Map<String, Object> searchFAQ(@RequestParam String query) {
        try {
            URL url = new URL(aiServiceUrl + "/api/faq/search?query=" +
                URLEncoder.encode(query, StandardCharsets.UTF_8));
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(10000);

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
            String response = reader.lines().collect(Collectors.joining());
            reader.close();

            Map<String, Object> result = objectMapper.readValue(response, Map.class);
            return result;
        } catch (Exception e) {
            log.error("FAQ搜索失败", e);
            return Map.of("results", Collections.emptyList());
        }
    }

    /**
     * 非流式对话（获取完整回复）
     * 先获取当前用户的记账数据作为上下文，再转发给Express后端
     */
    @PostMapping("/chat")
    public Map<String, Object> chat(@RequestBody Map<String, Object> body) {
        String sessionId = (String) body.get("sessionId");
        String message = (String) body.get("message");
        try {
            // 1. 获取当前登录用户ID
            Long userId = UserContext.getUser();
            if (userId == null) {
                return Map.of("error", "用户未登录");
            }

            // 2. 获取本月统计数据
            java.time.YearMonth now = java.time.YearMonth.now();
            MonthlyStatisticsVO monthlyStats = null;
            List<CategoryStatisticsVO> expenseCategories = Collections.emptyList();
            List<CategoryStatisticsVO> incomeCategories = Collections.emptyList();
            List<RecordVO> recentRecords = Collections.emptyList();

            try {
                monthlyStats = statisticsService.getMonthlyStats(userId, now.getYear(), now.getMonthValue());
                expenseCategories = statisticsService.getCategoryStats(userId, now.getYear(), now.getMonthValue(), 0);
                incomeCategories = statisticsService.getCategoryStats(userId, now.getYear(), now.getMonthValue(), 1);
            } catch (Exception e) {
                log.warn("获取月度统计失败（可能用户暂无数据）", e);
            }

            // 3. 获取最近10条账单记录
            try {
                var recordPage = recordsService.getRecordsById(userId, 1, 10, null, null);
                if (recordPage != null && recordPage.getRecords() != null) {
                    recentRecords = recordPage.getRecords();
                }
            } catch (Exception e) {
                log.warn("获取最近记录失败", e);
            }

            // 4. 构建上下文数据Map
            Map<String, Object> userContext = new LinkedHashMap<>();
            userContext.put("currentDate", now.toString());

            if (monthlyStats != null) {
                Map<String, Object> summary = new LinkedHashMap<>();
                summary.put("totalIncome", monthlyStats.getTotalIncome());
                summary.put("totalExpense", monthlyStats.getTotalExpense());
                summary.put("balance", monthlyStats.getBalance());
                userContext.put("monthSummary", summary);
            }

            if (!expenseCategories.isEmpty()) {
                List<Map<String, Object>> expenseList = new ArrayList<>();
                for (CategoryStatisticsVO cat : expenseCategories) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("category", cat.getCategoryName());
                    item.put("amount", cat.getAmount());
                    item.put("percentage", cat.getPercentage());
                    expenseList.add(item);
                }
                userContext.put("expenseBreakdown", expenseList);
            }

            if (!incomeCategories.isEmpty()) {
                List<Map<String, Object>> incomeList = new ArrayList<>();
                for (CategoryStatisticsVO cat : incomeCategories) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("category", cat.getCategoryName());
                    item.put("amount", cat.getAmount());
                    item.put("percentage", cat.getPercentage());
                    incomeList.add(item);
                }
                userContext.put("incomeBreakdown", incomeList);
            }

            if (!recentRecords.isEmpty()) {
                List<Map<String, Object>> recordList = new ArrayList<>();
                for (RecordVO r : recentRecords) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("date", r.getRecordDate() != null ? r.getRecordDate().toString() : "");
                    item.put("category", r.getCategoryName());
                    item.put("type", r.getCategoryType() != null ? (r.getCategoryType() == 0 ? "支出" : "收入") : "");
                    item.put("amount", r.getAmount());
                    item.put("remark", r.getRemark() != null ? r.getRemark() : "");
                    recordList.add(item);
                }
                userContext.put("recentRecords", recordList);
            }

            String contextJson = objectMapper.writeValueAsString(userContext);
            log.info("AI对话 - 用户{}的上下文数据大小: {}字节", userId, contextJson.length());

            // 5. 通过POST方式调用Express，携带上下文数据
            URL url = new URL(aiServiceUrl + "/api/chat");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setDoOutput(true);
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(120000);

            // 构建请求体：包含sessionId、message和用户上下文数据
            Map<String, Object> expressBody = new LinkedHashMap<>();
            expressBody.put("sessionId", sessionId);
            expressBody.put("message", message);
            expressBody.put("context", objectMapper.readValue(contextJson, Map.class));

            String jsonBody = objectMapper.writeValueAsString(expressBody);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
            }

            int code = conn.getResponseCode();
            BufferedReader reader = new BufferedReader(new InputStreamReader(
                code == 200 ? conn.getInputStream() : conn.getErrorStream(), StandardCharsets.UTF_8));
            String response = reader.lines().collect(Collectors.joining());
            reader.close();

            if (code != 200) {
                log.error("Express后端返回错误: code={}, body={}", code, response);
                return Map.of("error", "AI服务异常: " + response);
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> result = objectMapper.readValue(response, Map.class);

            // Express返回格式为 { answer: "..." }，统一转为 { content: "..." }
            Object answer = result.get("answer");
            if (answer != null) {
                return Map.of("content", answer.toString());
            }
            return result;

        } catch (Exception e) {
            log.error("AI对话失败", e);
            return Map.of("error", "对话失败: " + e.getMessage());
        }
    }
}
