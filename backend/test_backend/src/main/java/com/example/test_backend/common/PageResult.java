package com.example.test_backend.common;


import lombok.Data;
import java.util.List;

@Data
public class PageResult<T> {
    private List<T> records;
    private Long total;
    private Long pages;
    private Long current;
    private Long size;

    public PageResult() {
    }

    public PageResult(List<T> records, Long total) {
        this.records = records;
        this.total = total;
    }

    public PageResult(List<T> records, Long total, Long pages, Long current, Long size) {
        this.records = records;
        this.total = total;
        this.pages = pages;
        this.current = current;
        this.size = size;
    }
}


