package com.example.test_backend.Controller;

import com.example.test_backend.Service.StatisticsService;
import com.example.test_backend.common.Result;
import com.example.test_backend.entity.Vo.CategoryStatisticsVO;
import com.example.test_backend.entity.Vo.MonthlyStatisticsVO;
import com.example.test_backend.interceptor.UserContext;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/statistics")
@RequiredArgsConstructor
public class StatisticsController {

    private final StatisticsService statisticsService;

    @GetMapping("/monthly")
    public Result<MonthlyStatisticsVO> getMonthlyStats(
            @RequestParam Integer year,
            @RequestParam Integer month
    ) {
        Long userId = UserContext.getUser();
        MonthlyStatisticsVO data = statisticsService.getMonthlyStats(userId, year, month);
        return Result.success(data);
    }

    @GetMapping("/category")
    public Result<List<CategoryStatisticsVO>> getCategoryStats(
            @RequestParam Integer year,
            @RequestParam Integer month,
            @RequestParam(defaultValue = "0") Integer type
    ) {
        Long userId = UserContext.getUser();
        List<CategoryStatisticsVO> data = statisticsService.getCategoryStats(userId, year, month, type);
        return Result.success(data);
    }
}
