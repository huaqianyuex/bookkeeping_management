package com.example.test_backend.Service;

import com.example.test_backend.entity.Vo.CategoryStatisticsVO;
import com.example.test_backend.entity.Vo.MonthlyStatisticsVO;

import java.util.List;

public interface StatisticsService {
    MonthlyStatisticsVO getMonthlyStats(Long userId, Integer year, Integer month);
    List<CategoryStatisticsVO> getCategoryStats(Long userId, Integer year, Integer month, Integer type);
}
