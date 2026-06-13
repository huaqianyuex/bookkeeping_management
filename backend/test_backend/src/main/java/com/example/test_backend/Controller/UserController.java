package com.example.test_backend.Controller;

import com.example.test_backend.Service.UserService;
import com.example.test_backend.common.Result;
import com.example.test_backend.entity.User;
import com.example.test_backend.entity.Vo.UserVO;
import com.example.test_backend.entity.dto.LoginDTO;
import com.example.test_backend.entity.dto.PasswordUpdateDTO;
import com.example.test_backend.entity.dto.RegisterDTO;
import com.example.test_backend.entity.dto.UserProfileUpdateDTO;
import com.example.test_backend.interceptor.UserContext;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @PostMapping("/register")
    public Result<UserVO> register(@Valid @RequestBody RegisterDTO registerDTO) {
        User user = userService.register(registerDTO);
        return Result.success("注册成功", userService.getUserInfo(user.getId()));
    }

    @PostMapping("/login")
    public Result<String> login(@Valid @RequestBody LoginDTO loginDTO) {
        String token = userService.login(loginDTO);
        return Result.success("登录成功", token);
    }

    @GetMapping("/info")
    public Result<UserVO> info() {
        Long userId = UserContext.getUser();
        UserVO userVO = userService.getUserInfo(userId);
        return Result.success(userVO);
    }

    @PutMapping("/info")
    public Result<UserVO> updateInfo(@Valid @RequestBody UserProfileUpdateDTO updateDTO) {
        Long userId = UserContext.getUser();
        UserVO userVO = userService.updateProfile(userId, updateDTO);
        return Result.success("资料更新成功", userVO);
    }

    @PostMapping(value = "/avatar", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<UserVO> uploadAvatar(@RequestParam("file") MultipartFile file) {
        Long userId = UserContext.getUser();
        UserVO userVO = userService.updateAvatar(userId, file);
        return Result.success("头像上传成功", userVO);
    }

    @PutMapping("/password")
    public Result<String> update_password(@Valid @RequestBody PasswordUpdateDTO passwordUpdateDTO) {
        Long userId = UserContext.getUser();
        userService.update_password(userId, passwordUpdateDTO.getOldPassword(), passwordUpdateDTO.getNewPassword());
        return Result.success("修改成功", null);
    }
}
