package com.example.test_backend.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.test_backend.entity.Record;
import com.example.test_backend.entity.Vo.CategoryStatisticsVO;
import com.example.test_backend.entity.Vo.MonthlyStatisticsVO;
import com.example.test_backend.entity.Vo.RecordVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface RecordMapper extends BaseMapper<Record> {

    RecordVO selectRecordVOById(@Param("id") Long id);

    @Select("SELECT" +
            "  #{year} AS year," +
            "  #{month} AS month," +
            "  COALESCE(SUM(CASE WHEN c.type = 1 THEN r.amount ELSE 0 END), 0) AS totalIncome," +
            "  COALESCE(SUM(CASE WHEN c.type = 0 THEN r.amount ELSE 0 END), 0) AS totalExpense" +
            " FROM record r" +
            " LEFT JOIN category c ON r.category_id = c.id" +
            " WHERE r.user_id = #{userId}" +
            "  AND YEAR(r.record_date) = #{year}" +
            "  AND MONTH(r.record_date) = #{month}")
    MonthlyStatisticsVO getMonthlyStats(@Param("userId") Long userId,
                                        @Param("year") Integer year,
                                        @Param("month") Integer month);

    @Select("SELECT" +
            "  c.id AS categoryId," +
            "  c.name AS categoryName," +
            "  COALESCE(SUM(r.amount), 0) AS amount" +
            " FROM record r" +
            " LEFT JOIN category c ON r.category_id = c.id" +
            " WHERE r.user_id = #{userId}" +
            "  AND YEAR(r.record_date) = #{year}" +
            "  AND MONTH(r.record_date) = #{month}" +
            "  AND c.type = #{type}" +
            " GROUP BY c.id, c.name" +
            " ORDER BY amount DESC")
    List<CategoryStatisticsVO> getCategoryStats(@Param("userId") Long userId,
                                                 @Param("year") Integer year,
                                                 @Param("month") Integer month,
                                                 @Param("type") Integer type);
}
