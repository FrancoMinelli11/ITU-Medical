import { Navigate, Outlet } from "react-router-dom";

export interface RoleRouteProps {
  roles: string[];
  userRole?: string;
}

export function RoleRoute({ roles, userRole }: RoleRouteProps) {
  if (!userRole) return <Navigate to="/login" replace />;
  if (!roles.includes(userRole)) return <Navigate to="/" replace />;
  return <Outlet />;
}
