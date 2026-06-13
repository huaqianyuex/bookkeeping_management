package com.example.test_backend.Service.impl;

import com.example.test_backend.Mapper.RecordMapper;
import com.example.test_backend.Service.StatisticsService;
import com.example.test_backend.entity.Vo.CategoryStatisticsVO;
import com.example.test_backend.entity.Vo.MonthlyStatisticsVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

@Service
@RequiredArgsConstructor
public class StatisticsServiceImpl implements StatisticsService {

    private final RecordMapper recordMapper;

    @Override
    public MonthlyStatisticsVO getMonthlyStats(Long userId, Integer year, Integer month) {
        MonthlyStatisticsVO vo = recordMapper.getMonthlyStats(userId, year, month);
        if (vo == null) {
            vo = new MonthlyStatisticsVO();
            vo.setYear(year);
            vo.setMonth(month);
            vo.setTotalIncome(BigDecimal.ZERO);
            vo.setTotalExpense(BigDecimal.ZERO);
        }
        vo.setBalance(vo.getTotalIncome().subtract(vo.getTotalExpense()));
        return vo;
    }

    @Override
    public List<CategoryStatisticsVO> getCategoryStats(Long userId, Integer year, Integer month, Integer type) {
        List<CategoryStatisticsVO> list = recordMapper.getCategoryStats(userId, year, month, type);
        BigDecimal total = list.stream()
                .map(CategoryStatisticsVO::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        for (CategoryStatisticsVO vo : list) {
            if (total.compareTo(BigDecimal.ZERO) > 0) {
                double pct = vo.getAmount().divide(total, 4, RoundingMode.HALF_UP)
                        .multiply(BigDecimal.valueOf(100))
                        .setScale(1, RoundingMode.HALF_UP)
                        .doubleValue();
                vo.setPercentage(pct);
            } else {
                vo.setPercentage(0.0);
            }
        }
        return list;
    }
}
