/**
 * ProgressBar Component
 * 
 * Animated progress bar with gradient fill.
 */

interface ProgressBarProps {
  progress: number; // 0-100
  label?: string;
  showPercentage?: boolean;
}

export function ProgressBar({ 
  progress, 
  label,
  showPercentage = true 
}: ProgressBarProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className="progress-container">
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
      {(label || showPercentage) && (
        <div className="progress-label">
          <span>{label || 'Progress'}</span>
          {showPercentage && <span>{Math.round(clampedProgress)}%</span>}
        </div>
      )}
    </div>
  );
}

export default ProgressBar;
