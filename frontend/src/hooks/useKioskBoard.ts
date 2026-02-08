import { useEffect } from 'react';

declare global {
  interface Window {
    kioskBoardLoaded?: Promise<void>;
    KioskBoard?: {
      init: (options: Record<string, unknown>) => void;
      run: (selector: string) => void;
    };
  }
}

function loadKioskBoard(): Promise<void> {
  if (window.KioskBoard) {
    return Promise.resolve();
  }
  if (window.kioskBoardLoaded) {
    return window.kioskBoardLoaded;
  }

  const basePath = window.location.pathname.startsWith('/pianolog') ? '/pianolog' : '';

  window.kioskBoardLoaded = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `${basePath}/static/kioskboard/kioskboard-aio-2.3.0.min.js`;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load KioskBoard'));
    document.head.appendChild(script);
  });

  return window.kioskBoardLoaded;
}

export function useKioskBoard(trigger?: unknown): void {
  const runKeyboard = () => {
    if (!window.KioskBoard) {
      return;
    }
    // Delay binding until newly mounted form inputs exist in the DOM.
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        window.KioskBoard?.run('.kioskboard-input');
      });
    });
  };

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const isKioskMode = urlParams.get('kiosk') === 'true';

    if (!isKioskMode) {
      return;
    }

    let cancelled = false;

    void loadKioskBoard()
      .then(() => {
        if (cancelled || !window.KioskBoard) {
          return;
        }

        window.KioskBoard.init({
          keysArrayOfObjects: [
            { '0': 'Q', '1': 'W', '2': 'E', '3': 'R', '4': 'T', '5': 'Y', '6': 'U', '7': 'I', '8': 'O', '9': 'P' },
            { '0': 'A', '1': 'S', '2': 'D', '3': 'F', '4': 'G', '5': 'H', '6': 'J', '7': 'K', '8': 'L' },
            { '0': 'Z', '1': 'X', '2': 'C', '3': 'V', '4': 'B', '5': 'N', '6': 'M' }
          ],
          keysArrayOfNumbers: [
            { '0': '7', '1': '8', '2': '9' },
            { '0': '4', '1': '5', '2': '6' },
            { '0': '1', '1': '2', '2': '3' },
            { '0': '0' }
          ],
          theme: 'light',
          capsLockActive: false,
          allowRealKeyboard: true,
          allowMobileKeyboard: false,
          cssAnimations: true,
          cssAnimationsDuration: 360,
          cssAnimationsStyle: 'slide',
          keysAllowSpacebar: true,
          keysSpacebarText: 'Space',
          keysEnterText: 'Close',
          keysEnterCanClose: true,
          keysFontFamily: 'sans-serif',
          keysFontSize: '22px',
          keysFontWeight: 'normal',
          keysIconSize: '25px'
        });

        runKeyboard();
      })
      .catch((error) => {
        console.error('Failed to load KioskBoard:', error);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const isKioskMode = urlParams.get('kiosk') === 'true';
    if (!isKioskMode) {
      return;
    }

    void loadKioskBoard()
      .then(() => {
        runKeyboard();
      })
      .catch((error) => {
        console.error('Failed to load KioskBoard:', error);
      });
  }, [trigger]);
}
