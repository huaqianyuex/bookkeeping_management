package com.example.test_backend.Service;

import com.example.test_backend.common.PageResult;
import com.example.test_backend.entity.Vo.AdminOverviewVO;
import com.example.test_backend.entity.Vo.AdminRecordVO;
import com.example.test_backend.entity.Vo.UserVO;

import java.util.List;

public interface AdminService {
    PageResult<UserVO> getUserList(Integer page, Integer size, String keyword);
    UserVO getUserDetail(Long userId);
    void deleteUser(Long userId);
    void batchDeleteUsers(List<Long> ids);
    PageResult<AdminRecordVO> getAllRecords(Integer page, Integer size, Integer type, String month, Long userId);
    void batchDeleteRecords(List<Long> ids);
    AdminOverviewVO getOverview();
}
