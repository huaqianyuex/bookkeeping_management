package com.example.test_backend.Service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.test_backend.Mapper.CategoryMapper;
import com.example.test_backend.Mapper.RecordMapper;
import com.example.test_backend.Service.RecordsService;

import com.example.test_backend.common.PageResult;
import com.example.test_backend.entity.Category;
import com.example.test_backend.entity.Record;
import com.example.test_backend.entity.Vo.RecordVO;
import com.example.test_backend.entity.dto.RecordDTO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RecordsServiceImpl implements RecordsService {

    private final RecordMapper recordMapper;
    private final CategoryMapper categoryMapper;

    @Override
    public PageResult<RecordVO> getRecordsById(Long userId, Integer page, Integer size,
                                         Long categoryId, String month) {

        Page<Record> pageObj = new Page<>(page, size);

        QueryWrapper<Record> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId);
        if (categoryId != null) {
            wrapper.eq("category_id", categoryId);
        }
        if (month != null) {
            wrapper.likeRight("record_date", month);
        }
        wrapper.orderByDesc("record_date", "create_time");

        Page<Record> resultPage = recordMapper.selectPage(pageObj, wrapper);

        List<RecordVO> voList = resultPage.getRecords().stream().map(record -> {
            RecordVO vo = new RecordVO();
            vo.setId(record.getId());
            vo.setUserId(record.getUserId());
            vo.setCategoryId(record.getCategoryId());
            vo.setAmount(record.getAmount());
            vo.setRemark(record.getRemark());
            vo.setRecordDate(record.getRecordDate());
            vo.setCreateTime(record.getCreateTime());
            vo.setUpdateTime(record.getUpdateTime());

            Category category = categoryMapper.selectById(record.getCategoryId());
            if (category != null) {
                vo.setCategoryName(category.getName());
                vo.setCategoryType(category.getType());
            }

            return vo;
        }).collect(Collectors.toList());

        return new PageResult<>(voList, resultPage.getTotal(),
                (long) resultPage.getPages(), resultPage.getCurrent(), resultPage.getSize());
    }

    @Override
    public RecordVO getRecordDetail(Long userId, Long recordId) {
        RecordVO vo = recordMapper.selectRecordVOById(recordId);
        if (vo == null || !vo.getUserId().equals(userId)) {
            throw new RuntimeException("记录不存在");
        }
        return vo;
    }

    @Override
    public RecordVO addRecord(Long userId, RecordDTO recordDTO) {
        Long categoryId = recordDTO.getCategoryId();
        Category category = categoryMapper.selectById(categoryId);
        if (category == null || !category.getUserId().equals(userId)) {
            throw new RuntimeException("分类不存在");
        }

        Record record = new Record();
        record.setUserId(userId);
        record.setCategoryId(recordDTO.getCategoryId());
        record.setAmount(recordDTO.getAmount());
        record.setRemark(recordDTO.getRemark());
        record.setRecordDate(LocalDate.parse(recordDTO.getRecordDate()));

        recordMapper.insert(record);

        return recordMapper.selectRecordVOById(record.getId());
    }

    @Override
    public RecordVO updateRecord(Long userId, Long recordId, RecordDTO recordDTO) {
        Record existing = recordMapper.selectById(recordId);
        if (existing == null || !existing.getUserId().equals(userId)) {
            throw new RuntimeException("记录不存在");
        }

        Long categoryId = recordDTO.getCategoryId();
        Category category = categoryMapper.selectById(categoryId);
        if (category == null || !category.getUserId().equals(userId)) {
            throw new RuntimeException("分类不存在");
        }

        Record record = new Record();
        record.setId(recordId);
        record.setCategoryId(recordDTO.getCategoryId());
        record.setAmount(recordDTO.getAmount());
        record.setRemark(recordDTO.getRemark());
        record.setRecordDate(LocalDate.parse(recordDTO.getRecordDate()));

        recordMapper.updateById(record);

        return recordMapper.selectRecordVOById(recordId);
    }

    @Override
    public void deleteRecord(Long userId, Long recordId) {
        Record record = recordMapper.selectById(recordId);
        if (record == null || !record.getUserId().equals(userId)) {
            throw new RuntimeException("记录不存在");
        }
        recordMapper.deleteById(recordId);
    }

}

