package com.example.test_backend.Controller;

import com.example.test_backend.Service.CategoryService;
import com.example.test_backend.common.Result;
import com.example.test_backend.entity.Category;
import com.example.test_backend.entity.dto.CategoryDTO;
import com.example.test_backend.interceptor.UserContext;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;


@RestController
@RequestMapping("/api/categories")
@RequiredArgsConstructor
public class CategoryController {
    private final CategoryService categoryService;

    @PostMapping
    public Result<Category> addCategory(@Valid @RequestBody CategoryDTO categoryDTO) {
        Long userId = UserContext.getUser();
        Category category = new Category();
        category.setName(categoryDTO.getName());
        category.setType(categoryDTO.getType());
        category.setUserId(userId);
        categoryService.save(category);
        return Result.success("新增成功", category);
    }

    @GetMapping
    public Result<List<Category>> list(@RequestParam(required = false) Integer type) {
        Long userId = UserContext.getUser();
        List<Category> list = categoryService.list(type, userId);
        return Result.success(list);
    }

    @PutMapping("/{id}")
    public Result<Category> updateCategory(@PathVariable Long id, @Valid @RequestBody CategoryDTO categoryDTO) {
        Long userId = UserContext.getUser();
        Category category = categoryService.updateCategory(userId, id, categoryDTO.getName(), categoryDTO.getType());
        return Result.success("修改成功", category);
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteCategory(@PathVariable Long id) {
        Long userId = UserContext.getUser();
        categoryService.deleteCategory(userId, id);
        return Result.success("删除成功", null);
    }

}
