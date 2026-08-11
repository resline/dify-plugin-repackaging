import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { fireEvent, render, screen } from '../../test/utils/test-utils';
import useAppStore from '../../stores/appStore';

vi.mock('../TaskStatus', () => ({
  default: () => <div>Task status content</div>,
}));

import ProcessingPanel from '../ProcessingPanel';

describe('ProcessingPanel', () => {
  const onClose = vi.fn();

  beforeEach(() => {
    onClose.mockClear();
    useAppStore.setState({ isProcessingPanelMinimized: false });
  });

  const renderPanel = () => render(
    <ProcessingPanel
      taskId="completed-task"
      onComplete={vi.fn()}
      onError={vi.fn()}
      onClose={onClose}
    />
  );

  it('closes from its visible close button', async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole('button', { name: 'Close task result' }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes when Escape is pressed', () => {
    renderPanel();

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes when the desktop backdrop is clicked', () => {
    renderPanel();

    fireEvent.mouseDown(screen.getByTestId('processing-panel-backdrop'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
