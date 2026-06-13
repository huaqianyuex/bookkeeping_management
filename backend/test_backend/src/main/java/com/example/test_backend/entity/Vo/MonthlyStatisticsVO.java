package com.example.test_backend.entity.Vo;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class MonthlyStatisticsVO {
    private Integer year;
    private Integer month;
    private BigDecimal totalIncome;
    private BigDecimal totalExpense;
    private BigDecimal balance;
}
