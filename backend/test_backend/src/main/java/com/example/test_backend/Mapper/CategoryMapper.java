package com.example.test_backend.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.test_backend.entity.Category;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface CategoryMapper extends BaseMapper<Category> {
    @Select("SELECT * FROM category WHERE user_id = 1 AND type = 0 ORDER BY create_time DESC")
    List<Category> select_List();


    @Select("select * from category where user_id=#{userId} ORDER BY create_time DESC")
    List<Category> select_List_By_id(Long userId);

//
//    @Update("UPDATE category SET name = #{newCategoryName}, update_time = NOW() WHERE id = #{id}")
//
//    void update_ById(@Param("id") Long id, @Param("newCategoryName") String newCategoryName);
@Update("UPDATE category SET name = #{newCategoryName}, update_time = NOW() WHERE id = #{id} AND name = #{oldCategoryName}")
int updateCategoryName(@Param("id") Long id, @Param("oldCategoryName") String oldCategoryName, @Param("newCategoryName") String newCategoryName);


}



