import express from 'express';
import cors from 'cors';
import { Database } from './db.js';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// 初始化数据库
const db = new Database();

// 异步初始化数据库
async function startServer() {
  await db.init();

  app.use(cors({
    origin: process.env.CORS_ORIGIN?.split(',') || true,
    credentials: true,
  }));
  app.use(express.json());

  // ==================== 非流式对话接口（uni-app 移动端专用） ====================

  app.post('/api/chat', async (req, res) => {
    try {
      const { sessionId, message, context } = req.body;

      if (!sessionId || !message) {
        return res.status(400).json({ error: '缺少参数' });
      }

      // 保存用户消息到数据库
      const userMsgId = db.addMessage(sessionId, 'user', message);

      // 构建系统提示词（支持动态注入用户记账数据）
      let systemPrompt = buildSystemPrompt(context);

      // 获取历史消息
      const historyMessages = db.getSessionMessages(sessionId);
      const contextMessages = historyMessages.slice(-10).map(msg => ({
        role: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content
      }));

      // 调用 Agnes AI API
      const apiUrl = 'https://apihub.agnes-ai.com/v1/chat/completions';
      const apiResponse = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.AGNES_API_KEY || 'your-api-key-here'}`,
        },
        body: JSON.stringify({
          model: 'agnes-2.0-flash',
          messages: [
            { role: 'system', content: systemPrompt },
            ...contextMessages,
            { role: 'user', content: message }
          ],
          stream: false,
        }),
      });

      if (!apiResponse.ok) {
        throw new Error(`API 请求失败: ${apiResponse.statusText}`);
      }

      const data = await apiResponse.json();
      const reply = data.choices?.[0]?.message?.content || '抱歉，暂时无法回复';

      // 保存助手回复到数据库
      db.addMessage(sessionId, 'assistant', reply);

      res.json({ answer: reply });
    } catch (error) {
      console.error('Chat error:', error);
      res.status(500).json({ error: '对话处理失败' });
    }
  });

  /**
   * 构建系统提示词（根据用户记账数据动态生成）
   * @param userContext - 可选的用户记账上下文数据
   */
  function buildSystemPrompt(userContext?: any): string {
    const basePrompt = `你是一个智能记账分析助手。你的职责是：
1. 帮助用户记录和管理日常消费
2. 分析用户的消费习惯和账单
3. 回答关于记账和财务管理的问题
4. 提供消费建议和预算规划

请友好、专业地回答用户的问题。如果用户询问与记账无关的问题，请礼貌地引导用户回到记账相关话题。`;

    // 如果没有用户数据，返回基础提示词
    if (!userContext) {
      return basePrompt;
    }

    // 有用户数据时，构建增强版提示词
    let dataSection = '\n\n## 当前用户的记账数据\n\n';
    dataSection += `**统计时间**: ${userContext.currentDate || '未知'}\n\n`;

    if (userContext.monthSummary) {
      const s = userContext.monthSummary;
      dataSection += `### 本月概况\n`;
      dataSection += `- 总收入: ¥${s.totalIncome ?? '0'}\n`;
      dataSection += `- 总支出: ¥${s.totalExpense ?? '0'}\n`;
      dataSection += `- 结余: ¥${s.balance ?? '0'}\n\n`;

      // 计算储蓄率
      const income = parseFloat(String(s.totalIncome || 0));
      const expense = parseFloat(String(s.totalExpense || 0));
      if (income > 0) {
        const savingsRate = ((income - expense) / income * 100).toFixed(1);
        dataSection += `- 本月储蓄率: ${savingsRate}%\n\n`;
      }
    }

    if (userContext.expenseBreakdown && userContext.expenseBreakdown.length > 0) {
      dataSection += `### 支出分类明细\n`;
      for (const item of userContext.expenseBreakdown) {
        dataSection += `- ${item.category}: ¥${item.amount} (${item.percentage}%)\n`;
      }
      dataSection += `\n`;
    }

    if (userContext.incomeBreakdown && userContext.incomeBreakdown.length > 0) {
      dataSection += `### 收入分类明细\n`;
      for (const item of userContext.incomeBreakdown) {
        dataSection += `- ${item.category}: ¥${item.amount} (${item.percentage}%)\n`;
      }
      dataSection += `\n`;
    }

    if (userContext.recentRecords && userContext.recentRecords.length > 0) {
      dataSection += `### 最近交易记录\n`;
      for (const r of userContext.recentRecords) {
        dataSection += `- [${r.date}] ${r.type} | ${r.category}: ¥${r.amount}${r.remark ? ' (' + r.remark + ')' : ''}\n`;
      }
      dataSection += `\n`;
    }

    dataSection += `---\n`;
    dataSection += `请基于以上数据分析用户的消费习惯，提供个性化的建议。注意：金额单位是人民币（元）。如果用户要求分析或建议，务必引用具体数据来支撑你的观点。`;

    return basePrompt + dataSection;
  }

  // ==================== API 路由 ====================

  // 创建新会话
  app.post('/api/sessions', async (req, res) => {
    try {
      const { title } = req.body;
      const sessionId = db.createSession(title || '新对话');
      res.json({ id: sessionId, title: title || '新对话' });
    } catch (error) {
      res.status(500).json({ error: '创建会话失败' });
    }
  });

  // 获取所有会话
  app.get('/api/sessions', async (req, res) => {
    try {
      const sessions = db.getAllSessions();
      res.json(sessions);
    } catch (error) {
      res.status(500).json({ error: '获取会话失败' });
    }
  });

  // 获取单个会话
  app.get('/api/sessions/:id', async (req, res) => {
    try {
      const session = db.getSession(req.params.id);
      if (!session) {
        return res.status(404).json({ error: '会话不存在' });
      }
      res.json(session);
    } catch (error) {
      res.status(500).json({ error: '获取会话失败' });
    }
  });

  // 删除会话
  app.delete('/api/sessions/:id', async (req, res) => {
    try {
      db.deleteSession(req.params.id);
      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: '删除会话失败' });
    }
  });

  // 获取会话的所有消息
  app.get('/api/sessions/:id/messages', async (req, res) => {
    try {
      const messages = db.getSessionMessages(req.params.id);
      res.json(messages);
    } catch (error) {
      res.status(500).json({ error: '获取消息失败' });
    }
  });

  // SSE 流式对话接口
  app.get('/api/chat/stream', async (req, res) => {
    const { sessionId, message, context } = req.query;

    if (!sessionId || !message) {
      return res.status(400).json({ error: '缺少参数' });
    }

    // 设置 SSE 头
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    try {
      // 保存用户消息到数据库
      const userMsgId = db.addMessage(sessionId as string, 'user', message as string);

      // 发送用户消息 ID
      res.write(`data: ${JSON.stringify({ type: 'user_msg_id', id: userMsgId })}\n\n`);

      // 构建系统提示词（智能记账分析系统，支持动态数据注入）
      let contextData = undefined;
      if (context && typeof context === 'string') {
        try { contextData = JSON.parse(context); } catch (e) { /* ignore */ }
      }
      const systemPrompt = buildSystemPrompt(contextData);

      // 获取历史消息用于上下文
      const historyMessages = db.getSessionMessages(sessionId as string);
      const contextMessages = historyMessages.slice(-10).map(msg => ({
        role: msg.role === 'user' ? 'user' as const : 'assistant' as const,
        content: msg.content
      }));

      // 调用 Agnes AI API 进行对话（使用 fetch）
      const apiUrl = 'https://apihub.agnes-ai.com/v1/chat/completions';
      const requestBody = {
        model: 'agnes-2.0-flash',
        messages: [
          { role: 'system', content: systemPrompt },
          ...contextMessages,
          { role: 'user', content: message as string }
        ],
        stream: true,
      };

      const apiResponse = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.AGNES_API_KEY || 'your-api-key-here'}`,
        },
        body: JSON.stringify(requestBody),
      });

      if (!apiResponse.ok) {
        throw new Error(`API 请求失败: ${apiResponse.statusText}`);
      }

      let fullResponse = '';

      // 处理 SSE 流式响应
      const reader = apiResponse.body!.getReader();
      const decoder = new TextDecoder();

      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));

                if (data.choices && data.choices[0]) {
                  const content = data.choices[0].delta.content || '';
                  if (content) {
                    fullResponse += content;
                    res.write(`data: ${JSON.stringify({ type: 'content', content })}\n\n`);
                  }
                }
              } catch (e) {
                // 可能是 [DONE] 消息
                if (line.includes('[DONE]')) {
                  // 流式结束
                }
              }
            }
          }
        }
      }

      // 保存助手回复到数据库
      const assistantMsgId = db.addMessage(sessionId as string, 'assistant', fullResponse);

      // 发送完成信号
      res.write(`data: ${JSON.stringify({ type: 'done', id: assistantMsgId })}\n\n`);
      res.end();

    } catch (error) {
      console.error('Stream error:', error);
      res.write(`data: ${JSON.stringify({ type: 'error', error: '对话处理失败' })}\n\n`);
      res.end();
    }
  });

  // FAQ 知识库检索
  app.get('/api/faq/search', async (req, res) => {
    try {
      const { query } = req.query;
      if (!query) {
        return res.status(400).json({ error: '缺少查询参数' });
      }

      const results = db.searchFAQ(query as string);
      res.json(results);
    } catch (error) {
      res.status(500).json({ error: '搜索失败' });
    }
  });

  // 添加满意度评价
  app.post('/api/feedback', async (req, res) => {
    try {
      const { messageId, rating, comment } = req.body;
      db.addFeedback(messageId, rating, comment);
      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: '保存反馈失败' });
    }
  });

  // ==================== 管理后台 API ====================

  // 获取对话统计
  app.get('/api/admin/stats', async (req, res) => {
    try {
      const stats = db.getChatStats();
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: '获取统计失败' });
    }
  });

  // 获取所有对话记录（管理后台）
  app.get('/api/admin/conversations', async (req, res) => {
    try {
      const { page = 1, limit = 20 } = req.query;
      const conversations = db.getAllConversations(Number(page), Number(limit));
      res.json(conversations);
    } catch (error) {
      res.status(500).json({ error: '获取对话记录失败' });
    }
  });

  // 获取满意度统计
  app.get('/api/admin/satisfaction', async (req, res) => {
    try {
      const stats = db.getSatisfactionStats();
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: '获取满意度统计失败' });
    }
  });

  // 健康检查
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  app.listen(PORT, () => {
    console.log(` 聊天机器人服务器运行在 http://localhost:${PORT}`);
    console.log(` 管理后台 API: http://localhost:${PORT}/api/admin/stats`);
    console.log(` 健康检查: http://localhost:${PORT}/api/health`);
  });
}

startServer().catch(err => {
  console.error('服务器启动失败:', err);
  process.exit(1);
});
