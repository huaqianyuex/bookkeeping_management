package com.example.test_backend.entity.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class RecordDTO {

    @NotNull(message = "分类不能为空")
    private Long categoryId;

    @NotNull(message = "金额不能为空")
    @DecimalMin(value = "0.01", message = "金额必须大于0")
    private BigDecimal amount;

    private String remark;

    @NotNull(message = "日期不能为空")
    private String recordDate;
}
