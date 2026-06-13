package com.example.test_backend.interceptor;


public class UserContext {

    private static final ThreadLocal<Long> USER_ID = new ThreadLocal<>();
    private static final ThreadLocal<Integer> USER_ROLE = new ThreadLocal<>();

    public static void setUser(Long userId) {
        USER_ID.set(userId);
    }

    public static Long getUser() {
        return USER_ID.get();
    }

    public static void setRole(Integer role) {
        USER_ROLE.set(role);
    }

    public static Integer getRole() {
        return USER_ROLE.get();
    }

    public static void remove() {
        USER_ID.remove();
        USER_ROLE.remove();
    }
}
