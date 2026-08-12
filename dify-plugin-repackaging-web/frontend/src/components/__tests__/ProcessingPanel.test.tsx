import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { fireEvent, render, screen } from '../../test/utils/test-utils';
import useAppStore from '../../stores/appStore';

vi.mock('../TaskStatus', () => ({
  default: ({ onStatusChange }: { onStatusChange?: (task: any) => void }) => (
    <div>
      <span>Task status content</span>
      <button type="button" onClick={() => onStatusChange?.({ status: 'completed' })}>
        Emit completed status
      </button>
      <button type="button" onClick={() => onStatusChange?.({ status: 'failed' })}>
        Emit failed status
      </button>
    </div>
  ),
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

  it('shows the completed state after it is minimized', async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole('button', { name: 'Emit completed status' }));
    await user.click(screen.getByRole('button', { name: 'Minimize task result' }));

    expect(screen.getByText('Task completed successfully')).toBeInTheDocument();
    expect(screen.queryByText('Task in progress...')).not.toBeInTheDocument();
  });

  it('keeps receiving status updates while minimized', async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole('button', { name: 'Minimize task result' }));
    fireEvent.click(screen.getByRole('button', { name: 'Emit completed status', hidden: true }));

    expect(screen.getByText('Task completed successfully')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Completed Task' })).toBeInTheDocument();
  });
});
