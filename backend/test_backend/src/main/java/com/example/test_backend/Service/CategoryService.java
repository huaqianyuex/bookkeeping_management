package com.example.test_backend.Service;

import com.example.test_backend.entity.Category;

import java.util.List;

public interface CategoryService {

    List<Category> list(Integer type, Long userId);

    void save(Category category);

    Category updateCategory(Long userId, Long categoryId, String name, Integer type);

    void deleteCategory(Long userId, Long categoryId);
}
