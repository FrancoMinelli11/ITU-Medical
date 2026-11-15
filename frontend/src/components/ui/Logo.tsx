import { Icon } from "./Icon";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo">
      <span className="logo-mark">
        <Icon name="heart" size={20} />
        <i />
      </span>
      {!compact && (
        <span>
          ITU <b>Medical</b>
        </span>
      )}
    </div>
  );
}
