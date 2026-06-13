package com.example.test_backend.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
public class RegisterDTO {

    @NotBlank(message = "用户名不能为空")
    @Pattern(
            regexp = "^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$",
            message = "用户名需为2-20位中英文或数字组合"
    )
    private String username;

    @NotBlank(message = "密码不能为空")
    @Pattern(
            regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)[A-Za-z\\d]{8,16}$",
            message = "密码需为8-16位且包含大小写字母和数字"
    )
    private String password;
}
