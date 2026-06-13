package com.example.test_backend.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;
@Data

public class CategoryUpdateDTO {



        @NotBlank(message = "原分类不能为空")
        private String oldCategoryName;

        @NotBlank(message = "新分类不能为空")
        private String newCategoryName;
    }


