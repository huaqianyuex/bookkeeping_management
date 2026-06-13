package com.example.test_backend.entity.Vo;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class AdminOverviewVO {
    private Long totalUsers;
    private Long totalRecords;
    private BigDecimal totalIncome;
    private BigDecimal totalExpense;
    private Long totalCategories;
}
