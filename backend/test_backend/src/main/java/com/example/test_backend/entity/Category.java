package com.example.test_backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;
//
//@Data
//@TableName("Category")
//public class Category {
//    @TableId(type= IdType.AUTO)
//    private Long id;
//    private String name;
//    private Integer type; //0支出 1收入
//
//    public Integer getType() {
//        return type;
//    }
//
//    private Long userId;
//    @TableField(fill = FieldFill.INSERT)
//    private LocalDateTime createTime;
//    @TableField(fill = FieldFill.INSERT_UPDATE)
//    private LocalDateTime updateTime;
//}
@Data
@TableName("Category")
public class Category {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String name;
    private Integer type;
    private Long userId;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
