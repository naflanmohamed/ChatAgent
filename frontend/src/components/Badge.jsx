import { MoonStar } from "lucide-react";

export default function Badge({ size = 32 }) {
  return (
    <div className="badge-mark" style={{ width: size, height: size }} aria-hidden="true">
      <MoonStar size={size * 0.52} strokeWidth={2} />
    </div>
  );
}
