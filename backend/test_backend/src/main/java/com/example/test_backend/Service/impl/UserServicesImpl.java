package com.example.test_backend.Service.impl;

import com.example.test_backend.Mapper.UserMapper;
import com.example.test_backend.Service.UserService;
import com.example.test_backend.entity.User;
import com.example.test_backend.entity.Vo.UserVO;
import com.example.test_backend.entity.dto.LoginDTO;
import com.example.test_backend.entity.dto.RegisterDTO;
import com.example.test_backend.entity.dto.UserProfileUpdateDTO;
import com.example.test_backend.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class UserServicesImpl implements UserService {

    private static final long MAX_AVATAR_SIZE = 2L * 1024 * 1024;
    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of("image/jpeg", "image/png");
    private static final Set<String> ALLOWED_EXTENSIONS = Set.of(".jpg", ".jpeg", ".png");

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    @Value("${app.upload.avatar-dir:uploads/avatars}")
    private String avatarDir;

    @Value("${app.upload.avatar-url-prefix:/uploads/avatars/}")
    private String avatarUrlPrefix;

    @Override
    public User register(RegisterDTO registerDTO) {
        User existing = userMapper.getByUsername(registerDTO.getUsername());
        if (existing != null) {
            throw new RuntimeException("用户名已存在");
        }

        User user = new User();
        user.setUsername(registerDTO.getUsername());
        user.setPassword(passwordEncoder.encode(registerDTO.getPassword()));
        user.setRole(0);
        userMapper.insert(user);
        user.setPassword(null);
        return user;
    }

    @Override
    public String login(LoginDTO loginDTO) {
        User existing = userMapper.getByUsername(loginDTO.getUsername());
        if (existing == null) {
            throw new RuntimeException("用户未注册，请注册后登录");
        }
        if (!passwordEncoder.matches(loginDTO.getPassword(), existing.getPassword())) {
            throw new RuntimeException("密码错误");
        }
        return JwtUtil.generateToken(existing.getId());
    }

    @Override
    public UserVO getUserInfo(Long userId) {
        User user = userMapper.getUserById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        return buildUserVO(user);
    }

    @Override
    public UserVO updateProfile(Long userId, UserProfileUpdateDTO updateDTO) {
        User user = userMapper.getUserById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }

        String newUsername = updateDTO.getUsername().trim();
        if (!newUsername.equals(user.getUsername())) {
            int duplicate = userMapper.countByUsernameExcludeId(newUsername, userId);
            if (duplicate > 0) {
                throw new RuntimeException("用户名已存在");
            }
            userMapper.updateUsernameById(userId, newUsername);
        }

        return getUserInfo(userId);
    }

    @Override
    public UserVO updateAvatar(Long userId, MultipartFile file) {
        User user = userMapper.getUserById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }

        validateAvatar(file);

        String originalName = file.getOriginalFilename() == null ? "" : file.getOriginalFilename();
        String extension = getFileExtension(originalName);
        String filename = UUID.randomUUID().toString().replace("-", "") + extension;

        Path uploadRoot = Paths.get(avatarDir).toAbsolutePath().normalize();
        try {
            Files.createDirectories(uploadRoot);
            Path target = uploadRoot.resolve(filename).normalize();
            if (!target.startsWith(uploadRoot)) {
                throw new RuntimeException("非法文件路径");
            }
            Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);

            String oldAvatarUrl = user.getAvatarUrl();
            String avatarUrl = normalizeAvatarUrlPrefix() + filename;
            userMapper.updateAvatarById(userId, avatarUrl);
            deleteOldAvatarIfExists(oldAvatarUrl, uploadRoot);
        } catch (IOException e) {
            throw new RuntimeException("头像上传失败，请稍后重试");
        }

        return getUserInfo(userId);
    }

    @Override
    public String update_password(Long userId, String oldPassword, String newPassword) {
        User userData = userMapper.selectById(userId);
        if (userData == null) {
            throw new RuntimeException("用户不存在");
        }
        if (!passwordEncoder.matches(oldPassword, userData.getPassword())) {
            throw new RuntimeException("原密码错误");
        }

        String encryptedPassword = passwordEncoder.encode(newPassword);
        userMapper.updatePasswordById(userId, encryptedPassword);
        return newPassword;
    }

    private UserVO buildUserVO(User user) {
        UserVO userVO = new UserVO();
        userVO.setId(user.getId());
        userVO.setUsername(user.getUsername());
        userVO.setAvatarUrl(user.getAvatarUrl());
        userVO.setRole(user.getRole() != null ? user.getRole() : 0);
        userVO.setCreateTime(user.getCreateTime());
        userVO.setUpdateTime(user.getUpdateTime());
        return userVO;
    }

    private void validateAvatar(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new RuntimeException("请上传头像文件");
        }
        if (file.getSize() > MAX_AVATAR_SIZE) {
            throw new RuntimeException("头像大小不能超过2MB");
        }

        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType.toLowerCase(Locale.ROOT))) {
            throw new RuntimeException("头像仅支持JPG/PNG格式");
        }

        String originalName = file.getOriginalFilename() == null ? "" : file.getOriginalFilename().toLowerCase(Locale.ROOT);
        boolean extValid = ALLOWED_EXTENSIONS.stream().anyMatch(originalName::endsWith);
        if (!extValid) {
            throw new RuntimeException("头像仅支持JPG/PNG格式");
        }
    }

    private String getFileExtension(String filename) {
        int idx = filename.lastIndexOf('.');
        if (idx < 0) {
            throw new RuntimeException("文件扩展名不合法");
        }
        String ext = filename.substring(idx).toLowerCase(Locale.ROOT);
        if (!ALLOWED_EXTENSIONS.contains(ext)) {
            throw new RuntimeException("头像仅支持JPG/PNG格式");
        }
        return ext;
    }

    private String normalizeAvatarUrlPrefix() {
        String prefix = avatarUrlPrefix;
        if (!prefix.startsWith("/")) {
            prefix = "/" + prefix;
        }
        if (!prefix.endsWith("/")) {
            prefix = prefix + "/";
        }
        return prefix;
    }

    private void deleteOldAvatarIfExists(String oldAvatarUrl, Path uploadRoot) {
        if (oldAvatarUrl == null || oldAvatarUrl.isBlank()) {
            return;
        }
        String prefix = normalizeAvatarUrlPrefix();
        if (!oldAvatarUrl.startsWith(prefix)) {
            return;
        }
        String oldName = oldAvatarUrl.substring(prefix.length());
        if (oldName.isBlank()) {
            return;
        }

        try {
            Path oldPath = uploadRoot.resolve(oldName).normalize();
            if (oldPath.startsWith(uploadRoot)) {
                Files.deleteIfExists(oldPath);
            }
        } catch (IOException ignored) {
        }
    }
}
