package com.example.test_backend.Service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.test_backend.Mapper.CategoryMapper;
import com.example.test_backend.Service.CategoryService;
import com.example.test_backend.common.Result;
import com.example.test_backend.entity.Category;
import com.example.test_backend.entity.User;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.PathVariable;

import java.util.List;

@Service
@RequiredArgsConstructor
public class CategoryServiceImpl implements CategoryService {

    private final CategoryMapper categoryMapper;

    @Override
    public List<Category> list(Integer type, Long userId) {
        LambdaQueryWrapper<Category> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Category::getUserId, userId);
        if (type != null) {
            wrapper.eq(Category::getType, type);
        }
        wrapper.orderByDesc(Category::getCreateTime);
        return categoryMapper.selectList(wrapper);
    }

    @Override
    public void save(Category category) {
        categoryMapper.insert(category);
    }

    @Override
    public Category updateCategory(Long userId, Long categoryId, String name, Integer type) {
        Category category = categoryMapper.selectById(categoryId);
        if (category == null || !category.getUserId().equals(userId)) {
            throw new RuntimeException("分类不存在");
        }
        category.setName(name);
        category.setType(type);
        categoryMapper.updateById(category);
        return categoryMapper.selectById(categoryId);
    }

    @Override
    public void deleteCategory(Long userId, Long categoryId) {
        Category category = categoryMapper.selectById(categoryId);
        if (category == null || !category.getUserId().equals(userId)) {
            throw new RuntimeException("分类不存在");
        }
        categoryMapper.deleteById(categoryId);
    }

}
