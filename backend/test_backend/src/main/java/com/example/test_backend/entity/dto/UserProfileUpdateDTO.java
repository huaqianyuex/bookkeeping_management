package com.example.test_backend.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
public class UserProfileUpdateDTO {

    @NotBlank(message = "用户名不能为空")
    @Pattern(
            regexp = "^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$",
            message = "用户名需为2-20位中英文或数字组合"
    )
    private String username;
}
