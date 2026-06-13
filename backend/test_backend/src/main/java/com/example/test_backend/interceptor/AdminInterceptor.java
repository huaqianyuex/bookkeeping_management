package com.example.test_backend.interceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AdminInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) throws Exception {
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        Integer role = UserContext.getRole();
        if (role == null || role != 1) {
            response.setStatus(403);
            response.setContentType("application/json;charset=utf-8");
            response.getWriter().write("{\"code\":403,\"message\":\"无管理员权限\",\"data\":null}");
            return false;
        }
        return true;
    }
}
