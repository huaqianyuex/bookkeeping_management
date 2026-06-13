package com.example.test_backend.entity.Vo;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class CategoryStatisticsVO {
    private Long categoryId;
    private String categoryName;
    private BigDecimal amount;
    private Double percentage;
}
