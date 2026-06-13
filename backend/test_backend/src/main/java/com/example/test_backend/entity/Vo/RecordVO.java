package com.example.test_backend.entity.Vo;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class RecordVO {
    private Long id;
    private Long userId;
    private Long categoryId;
    private String categoryName;
    private Integer categoryType;
    private BigDecimal amount;
    private String remark;
    private LocalDate recordDate;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
