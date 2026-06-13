package com.example.test_backend.Service;

import com.example.test_backend.common.PageResult;
import com.example.test_backend.entity.Vo.RecordVO;
import com.example.test_backend.entity.dto.RecordDTO;

public interface RecordsService {
    PageResult<RecordVO> getRecordsById(Long userId, Integer page, Integer size,
                                        Long categoryId, String month);

    RecordVO getRecordDetail(Long userId, Long recordId);

    RecordVO addRecord(Long userId, RecordDTO recordDTO);

    RecordVO updateRecord(Long userId, Long recordId, RecordDTO recordDTO);

    void deleteRecord(Long userId, Long recordId);
}
