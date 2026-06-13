package com.example.test_backend.entity.Vo;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class UserVO {
    private Long id;
    private String username;
    private String avatarUrl;
    private Integer role;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
