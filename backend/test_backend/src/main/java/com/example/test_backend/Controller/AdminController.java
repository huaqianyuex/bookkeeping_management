package com.example.test_backend.Controller;

import com.example.test_backend.Service.AdminService;
import com.example.test_backend.common.PageResult;
import com.example.test_backend.common.Result;
import com.example.test_backend.entity.Vo.AdminOverviewVO;
import com.example.test_backend.entity.Vo.AdminRecordVO;
import com.example.test_backend.entity.Vo.UserVO;
import com.example.test_backend.entity.dto.BatchDeleteDTO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private final AdminService adminService;

    // 用户列表
    @GetMapping("/users")
    public Result<PageResult<UserVO>> getUserList(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) String keyword) {
        return Result.success(adminService.getUserList(page, size, keyword));
    }

    // 用户详情
    @GetMapping("/users/{id}")
    public Result<UserVO> getUserDetail(@PathVariable Long id) {
        return Result.success(adminService.getUserDetail(id));
    }

    // 删除用户
    @DeleteMapping("/users/{id}")
    public Result<Void> deleteUser(@PathVariable Long id) {
        adminService.deleteUser(id);
        return Result.success("删除成功", null);
    }

    // 批量删除用户
    @PostMapping("/users/batch-delete")
    public Result<Void> batchDeleteUsers(@Valid @RequestBody BatchDeleteDTO dto) {
        adminService.batchDeleteUsers(dto.getIds());
        return Result.success("批量删除成功", null);
    }

    // 所有账单
    @GetMapping("/records")
    public Result<PageResult<AdminRecordVO>> getAllRecords(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) Integer type,
            @RequestParam(required = false) String month,
            @RequestParam(required = false) Long userId) {
        return Result.success(adminService.getAllRecords(page, size, type, month, userId));
    }

    // 批量删除账单
    @PostMapping("/records/batch-delete")
    public Result<Void> batchDeleteRecords(@Valid @RequestBody BatchDeleteDTO dto) {
        adminService.batchDeleteRecords(dto.getIds());
        return Result.success("批量删除成功", null);
    }

    // 系统概览统计
    @GetMapping("/statistics/overview")
    public Result<AdminOverviewVO> getOverview() {
        return Result.success(adminService.getOverview());
    }
}
