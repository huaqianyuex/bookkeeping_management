package com.example.test_backend.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.test_backend.entity.Vo.MonthlyStatisticsVO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface StatisticsMapper extends BaseMapper<MonthlyStatisticsVO> {




    void get_monthly_records(Long userId, Integer year, Integer month);
}
