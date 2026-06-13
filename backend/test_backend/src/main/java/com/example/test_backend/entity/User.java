package com.example.test_backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("user")
public class User  {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String username;
    private String password;
    private String avatarUrl;
    private Integer role; // 0普通用户 1管理员
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

}
