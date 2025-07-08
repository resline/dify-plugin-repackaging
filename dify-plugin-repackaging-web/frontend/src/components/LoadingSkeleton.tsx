import React from 'react';

interface LoadingSkeletonProps {
  variant?: 'card' | 'text' | 'button' | 'circle';
  width?: string;
  height?: string;
  className?: string;
  count?: number;
}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  variant = 'text',
  width,
  height,
  className = '',
  count = 1
}) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'card':
        return 'w-full h-48 rounded-lg';
      case 'button':
        return 'w-24 h-10 rounded-md';
      case 'circle':
        return 'w-12 h-12 rounded-full';
      case 'text':
      default:
        return 'w-full h-4 rounded';
    }
  };

  const baseClasses = `animate-pulse bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%] ${getVariantClasses()} ${className}`;

  const style = {
    width: width || undefined,
    height: height || undefined,
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s infinite'
  };

  return (
    <>
      <style>
        {`
          @keyframes shimmer {
            0% {
              background-position: -200% 0;
            }
            100% {
              background-position: 200% 0;
            }
          }
        `}
      </style>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={baseClasses}
          style={style}
          role="status"
          aria-label="Loading"
        >
          <span className="sr-only">Loading...</span>
        </div>
      ))}
    </>
  );
};

export const CardSkeleton: React.FC<{ count?: number }> = ({ count = 1 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="bg-white rounded-lg shadow-md p-6 space-y-4">
          <div className="flex items-start space-x-4">
            <LoadingSkeleton variant="circle" width="48px" height="48px" />
            <div className="flex-1 space-y-2">
              <LoadingSkeleton width="60%" height="20px" />
              <LoadingSkeleton width="40%" height="16px" />
            </div>
          </div>
          <LoadingSkeleton count={2} className="mb-2" />
          <div className="flex justify-between items-center pt-4">
            <LoadingSkeleton width="80px" height="14px" />
            <LoadingSkeleton variant="button" />
          </div>
        </div>
      ))}
    </>
  );
};

export default LoadingSkeleton;