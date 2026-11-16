import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/features/auth/useAuth";
import type { Rol } from "@/features/auth/types";
import { Icon, type IconName } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";

const NOMBRE_ROL: Record<Rol, string> = {
  PACIENTE: "Paciente",
  RECEPCIONISTA: "Recepción",
  MEDICO: "Médico/a",
  ADMINISTRADOR: "Administrador/a",
};

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
}

export function AppShell() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (!usuario) return null;

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItems: NavItem[] = [
    { to: "/", label: "Inicio", icon: "home", end: true },
  ];

  if (usuario.rol === "PACIENTE") {
    navItems.push(
      { to: "/turnos", label: "Mis turnos", icon: "calendar" },
      { to: "/turnos/reservar", label: "Reservar turno", icon: "plus" },
    );
  }

  if (usuario.rol === "RECEPCIONISTA") {
    navItems.push({
      to: "/recepcion",
      label: "Recepción & Espera",
      icon: "people",
    });
  }

  if (usuario.rol === "MEDICO") {
    navItems.push({
      to: "/medico",
      label: "Consultorio Médico",
      icon: "stethoscope",
    });
  }

  if (usuario.rol === "ADMINISTRADOR") {
    navItems.push(
      { to: "/admin", label: "Gestión de Agendas", icon: "calendar" },
      { to: "/recepcion", label: "Recepción & Espera", icon: "people" },
      { to: "/medico", label: "Consultorio Médico", icon: "stethoscope" },
    );
  }

  const iniciales = `${usuario.nombre.charAt(0)}${usuario.apellido.charAt(0)}`.toUpperCase();

  return (
    <div className="app-shell">
      {/* Barra lateral */}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="sidebar-top">
          <Logo />
          <button
            type="button"
            className="mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
          >
            <Icon name="close" />
          </button>
        </div>

        <nav>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              <i />
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="help-card">
            <span>
              <Icon name="heart" size={18} />
            </span>
            <b>¿Necesitás ayuda?</b>
            <p>Estamos para acompañarte en tu atención.</p>
            <button type="button">Centro de ayuda</button>
          </div>
          <button type="button" className="logout" onClick={() => void handleLogout()}>
            <Icon name="logout" size={18} /> Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Contenido principal */}
      <main className="main">
        <header className="topbar">
          <button
            type="button"
            className="menu-button"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
          >
            <Icon name="menu" />
          </button>
          <Logo compact />

          <div className="top-actions">
            <button
              type="button"
              className="notification"
              aria-label="Notificaciones"
            >
              <Icon name="bell" />
              <i />
            </button>

            <div className="profile">
              <span>{iniciales}</span>
              <p>
                <b>{usuario.nombre} {usuario.apellido}</b>
                <small>{NOMBRE_ROL[usuario.rol]}</small>
              </p>
            </div>
          </div>
        </header>

        <div className="page">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
