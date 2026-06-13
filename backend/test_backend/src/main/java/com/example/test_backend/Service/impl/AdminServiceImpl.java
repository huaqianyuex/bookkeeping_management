package com.example.test_backend.Service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.test_backend.Mapper.CategoryMapper;
import com.example.test_backend.Mapper.RecordMapper;
import com.example.test_backend.Mapper.UserMapper;
import com.example.test_backend.Service.AdminService;
import com.example.test_backend.common.PageResult;
import com.example.test_backend.entity.Category;
import com.example.test_backend.entity.Record;
import com.example.test_backend.entity.User;
import com.example.test_backend.entity.Vo.AdminOverviewVO;
import com.example.test_backend.entity.Vo.AdminRecordVO;
import com.example.test_backend.entity.Vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AdminServiceImpl implements AdminService {

    private final UserMapper userMapper;
    private final RecordMapper recordMapper;
    private final CategoryMapper categoryMapper;

    @Override
    public PageResult<UserVO> getUserList(Integer page, Integer size, String keyword) {
        Page<User> pageObj = new Page<>(page, size);
        QueryWrapper<User> wrapper = new QueryWrapper<>();
        if (keyword != null && !keyword.trim().isEmpty()) {
            wrapper.like("username", keyword.trim());
        }
        wrapper.orderByDesc("create_time");
        Page<User> resultPage = userMapper.selectPage(pageObj, wrapper);

        List<UserVO> voList = resultPage.getRecords().stream().map(user -> {
            UserVO vo = new UserVO();
            vo.setId(user.getId());
            vo.setUsername(user.getUsername());
            vo.setRole(user.getRole() != null ? user.getRole() : 0);
            vo.setCreateTime(user.getCreateTime());
            vo.setUpdateTime(user.getUpdateTime());
            return vo;
        }).collect(Collectors.toList());

        return new PageResult<>(voList, resultPage.getTotal(),
                (long) resultPage.getPages(), resultPage.getCurrent(), resultPage.getSize());
    }

    @Override
    public UserVO getUserDetail(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        UserVO vo = new UserVO();
        vo.setId(user.getId());
        vo.setUsername(user.getUsername());
        vo.setRole(user.getRole() != null ? user.getRole() : 0);
        vo.setCreateTime(user.getCreateTime());
        vo.setUpdateTime(user.getUpdateTime());
        return vo;
    }

    @Override
    @Transactional
    public void deleteUser(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        if (user.getRole() != null && user.getRole() == 1) {
            throw new RuntimeException("不能删除管理员账户");
        }
        // 删除用户的所有账单
        QueryWrapper<Record> recordWrapper = new QueryWrapper<>();
        recordWrapper.eq("user_id", userId);
        recordMapper.delete(recordWrapper);
        // 删除用户的所有分类
        QueryWrapper<Category> categoryWrapper = new QueryWrapper<>();
        categoryWrapper.eq("user_id", userId);
        categoryMapper.delete(categoryWrapper);
        // 删除用户
        userMapper.deleteById(userId);
    }

    @Override
    @Transactional
    public void batchDeleteUsers(List<Long> ids) {
        for (Long userId : ids) {
            User user = userMapper.selectById(userId);
            if (user == null) continue;
            if (user.getRole() != null && user.getRole() == 1) {
                throw new RuntimeException("不能删除管理员账户: " + user.getUsername());
            }
            QueryWrapper<Record> recordWrapper = new QueryWrapper<>();
            recordWrapper.eq("user_id", userId);
            recordMapper.delete(recordWrapper);
            QueryWrapper<Category> categoryWrapper = new QueryWrapper<>();
            categoryWrapper.eq("user_id", userId);
            categoryMapper.delete(categoryWrapper);
            userMapper.deleteById(userId);
        }
    }

    @Override
    public PageResult<AdminRecordVO> getAllRecords(Integer page, Integer size, Integer type, String month, Long userId) {
        Page<Record> pageObj = new Page<>(page, size);
        QueryWrapper<Record> wrapper = new QueryWrapper<>();
        if (userId != null) {
            wrapper.eq("user_id", userId);
        }
        if (month != null && !month.isEmpty()) {
            wrapper.likeRight("record_date", month);
        }
        wrapper.orderByDesc("record_date", "create_time");
        Page<Record> resultPage = recordMapper.selectPage(pageObj, wrapper);

        List<AdminRecordVO> voList = resultPage.getRecords().stream().map(record -> {
            AdminRecordVO vo = new AdminRecordVO();
            vo.setId(record.getId());
            vo.setUserId(record.getUserId());
            vo.setCategoryId(record.getCategoryId());
            vo.setAmount(record.getAmount());
            vo.setRemark(record.getRemark());
            vo.setRecordDate(record.getRecordDate());
            vo.setCreateTime(record.getCreateTime());

            // 获取用户名
            User user = userMapper.selectById(record.getUserId());
            if (user != null) {
                vo.setUsername(user.getUsername());
            }

            // 获取分类信息
            Category category = categoryMapper.selectById(record.getCategoryId());
            if (category != null) {
                vo.setCategoryName(category.getName());
                vo.setCategoryType(category.getType());
            }

            return vo;
        }).collect(Collectors.toList());

        // 按类型过滤（在VO层面过滤）
        if (type != null) {
            voList = voList.stream()
                    .filter(v -> type.equals(v.getCategoryType()))
                    .collect(Collectors.toList());
        }

        return new PageResult<>(voList, resultPage.getTotal(),
                (long) resultPage.getPages(), resultPage.getCurrent(), resultPage.getSize());
    }

    @Override
    @Transactional
    public void batchDeleteRecords(List<Long> ids) {
        for (Long recordId : ids) {
            recordMapper.deleteById(recordId);
        }
    }

    @Override
    public AdminOverviewVO getOverview() {
        AdminOverviewVO vo = new AdminOverviewVO();

        // 总用户数
        vo.setTotalUsers(userMapper.selectCount(null));

        // 总账单数
        vo.setTotalRecords(recordMapper.selectCount(null));

        // 总分类数
        vo.setTotalCategories(categoryMapper.selectCount(null));

        // 全局收支统计
        QueryWrapper<Record> wrapper = new QueryWrapper<>();
        List<Record> allRecords = recordMapper.selectList(wrapper);

        BigDecimal totalIncome = BigDecimal.ZERO;
        BigDecimal totalExpense = BigDecimal.ZERO;

        for (Record record : allRecords) {
            Category category = categoryMapper.selectById(record.getCategoryId());
            if (category != null) {
                if (category.getType() == 1) {
                    totalIncome = totalIncome.add(record.getAmount());
                } else {
                    totalExpense = totalExpense.add(record.getAmount());
                }
            }
        }

        vo.setTotalIncome(totalIncome);
        vo.setTotalExpense(totalExpense);

        return vo;
    }
}
