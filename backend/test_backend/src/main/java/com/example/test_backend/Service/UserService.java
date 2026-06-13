package com.example.test_backend.Service;

import com.example.test_backend.entity.User;
import com.example.test_backend.entity.Vo.UserVO;
import com.example.test_backend.entity.dto.LoginDTO;
import com.example.test_backend.entity.dto.RegisterDTO;
import com.example.test_backend.entity.dto.UserProfileUpdateDTO;
import org.springframework.web.multipart.MultipartFile;

public interface UserService {

    User register(RegisterDTO registerDTO);

    String login(LoginDTO loginDTO);

    UserVO getUserInfo(Long userId);

    UserVO updateProfile(Long userId, UserProfileUpdateDTO updateDTO);

    UserVO updateAvatar(Long userId, MultipartFile file);

    String update_password(Long userId, String oldPassword, String newPassword);
}
