package com.example.test_backend.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.test_backend.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface UserMapper extends BaseMapper<User> {

    @Select("SELECT * FROM user WHERE username = #{username}")
    User getByUsername(String username);

    @Select("SELECT * FROM user WHERE id = #{userId}")
    User getUserById(Long userId);

    @Select("SELECT COUNT(1) FROM user WHERE username = #{username} AND id <> #{userId}")
    int countByUsernameExcludeId(@Param("username") String username, @Param("userId") Long userId);

    @Update("UPDATE user SET username = #{username}, update_time = NOW() WHERE id = #{id}")
    int updateUsernameById(@Param("id") Long id, @Param("username") String username);

    @Update("UPDATE user SET avatar_url = #{avatarUrl}, update_time = NOW() WHERE id = #{id}")
    int updateAvatarById(@Param("id") Long id, @Param("avatarUrl") String avatarUrl);

    @Update("UPDATE user SET password = #{password}, update_time = NOW() WHERE id = #{id}")
    int updatePasswordById(@Param("id") Long id, @Param("password") String password);
}
