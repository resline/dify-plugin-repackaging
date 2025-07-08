import React, { useEffect, useRef } from 'react';

interface ConfettiProps {
  active: boolean;
  duration?: number;
}

const Confetti: React.FC<ConfettiProps> = ({ active, duration = 3000 }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!active || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Confetti pieces
    const pieces: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      rotation: number;
      rotationSpeed: number;
      color: string;
    }> = [];

    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];
    const pieceCount = 150;

    // Initialize confetti pieces
    for (let i = 0; i < pieceCount; i++) {
      pieces.push({
        x: Math.random() * canvas.width,
        y: -10,
        vx: (Math.random() - 0.5) * 4,
        vy: Math.random() * 3 + 2,
        size: Math.random() * 6 + 4,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.2,
        color: colors[Math.floor(Math.random() * colors.length)]
      });
    }

    let animationId: number;
    const gravity = 0.1;
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      
      if (elapsed > duration) {
        cancelAnimationFrame(animationId);
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      pieces.forEach((piece) => {
        // Update position
        piece.vy += gravity;
        piece.x += piece.vx;
        piece.y += piece.vy;
        piece.rotation += piece.rotationSpeed;

        // Fade out near the end
        const fadeStart = duration * 0.7;
        let alpha = 1;
        if (elapsed > fadeStart) {
          alpha = 1 - (elapsed - fadeStart) / (duration - fadeStart);
        }

        // Draw piece
        ctx.save();
        ctx.translate(piece.x, piece.y);
        ctx.rotate(piece.rotation);
        ctx.globalAlpha = alpha;
        ctx.fillStyle = piece.color;
        ctx.fillRect(-piece.size / 2, -piece.size / 2, piece.size, piece.size);
        ctx.restore();

        // Reset pieces that fall off screen
        if (piece.y > canvas.height + 10) {
          piece.y = -10;
          piece.x = Math.random() * canvas.width;
          piece.vx = (Math.random() - 0.5) * 4;
          piece.vy = Math.random() * 3 + 2;
        }
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    // Handle window resize
    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
    };
  }, [active, duration]);

  if (!active) return null;

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-50"
      style={{
        width: '100%',
        height: '100%'
      }}
    />
  );
};

export default Confetti;