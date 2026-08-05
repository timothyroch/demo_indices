import { inject } from '@angular/core';
import { CanMatchFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

function createAuthGuard(
  check: (authService: AuthService) => boolean,
  redirectTo: string,
): CanMatchFn {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);
    if (check(authService)) {
      return true;
    }
    router.navigate([redirectTo]);
    return false;
  };
}

export const authGuard = createAuthGuard((authService) => authService.isAuthenticated, '/login');
export const adminGuard = createAuthGuard(
  (authService) => authService.isAuthenticated && authService.isAdmin,
  '/',
);
