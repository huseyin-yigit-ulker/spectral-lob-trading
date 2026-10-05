import { useState, useRef } from 'react';
import { createPortal } from 'react-dom';

export default function Tooltip({ text, children }) {
  const [show, setShow] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const ref = useRef(null);

  const handleMouseEnter = () => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      setPos({ x: rect.left + rect.width / 2, y: rect.top - 10 });
      setShow(true);
    }
  };

  return (
    <>
      <div 
        ref={ref} 
        onMouseEnter={handleMouseEnter} 
        onMouseLeave={() => setShow(false)} 
        className="inline-flex cursor-help items-center gap-1.5 transition-colors hover:text-gray-200"
      >
        {children}
      </div>
      {show && createPortal(
        <div 
          className="fixed z-[99999] w-64 bg-[#1E2329] text-gray-200 text-xs p-3.5 rounded-lg border border-[#2B3139] shadow-2xl pointer-events-none transform -translate-x-1/2 -translate-y-full leading-relaxed font-medium"
          style={{ left: pos.x, top: pos.y }}
        >
          {/* text icindeki yeni satirlari (\n) <br/> ile render edelim ki duzgun gorunsun */}
          {text.split('\n').map((line, i) => (
            <span key={i}>
              {line}
              {i !== text.split('\n').length - 1 && <br />}
            </span>
          ))}
          {/* Tooltip Ok ucu */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-[1px] border-[6px] border-transparent border-t-[#2B3139]"></div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-[2px] border-[5px] border-transparent border-t-[#1E2329]"></div>
        </div>,
        document.body
      )}
    </>
  );
}
