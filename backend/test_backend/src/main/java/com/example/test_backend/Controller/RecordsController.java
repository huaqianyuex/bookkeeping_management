package com.example.test_backend.Controller;

import com.example.test_backend.Service.RecordsService;
import com.example.test_backend.common.PageResult;
import com.example.test_backend.common.Result;
import com.example.test_backend.entity.Vo.RecordVO;
import com.example.test_backend.entity.dto.RecordDTO;
import com.example.test_backend.interceptor.UserContext;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;


@RestController
@RequestMapping("/api/records")
@RequiredArgsConstructor
public class RecordsController {
    private final RecordsService recordsService;

    @GetMapping
    public Result<PageResult<RecordVO>> getRecords(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer size,
            @RequestParam(required = false) Long categoryId,
            @RequestParam(required = false) String month
    ){
        Long userId = UserContext.getUser();
        PageResult<RecordVO> list = recordsService.getRecordsById(userId, page, size, categoryId, month);
        return Result.success(list);
    }

    @GetMapping("/{id}")
    public Result<RecordVO> getRecordDetail(@PathVariable Long id){
        Long userId = UserContext.getUser();
        RecordVO record = recordsService.getRecordDetail(userId, id);
        return Result.success(record);
    }

    @PostMapping
    public Result<RecordVO> addRecord(@Valid @RequestBody RecordDTO recordDTO){
        Long userId = UserContext.getUser();
        RecordVO record = recordsService.addRecord(userId, recordDTO);
        return Result.success("新增成功", record);
    }

    @PutMapping("/{id}")
    public Result<RecordVO> updateRecord(
            @PathVariable Long id,
            @Valid @RequestBody RecordDTO recordDTO){
        Long userId = UserContext.getUser();
        RecordVO record = recordsService.updateRecord(userId, id, recordDTO);
        return Result.success("修改成功", record);
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteRecord(@PathVariable Long id){
        Long userId = UserContext.getUser();
        recordsService.deleteRecord(userId, id);
        return Result.success("删除成功", null);
    }

}
