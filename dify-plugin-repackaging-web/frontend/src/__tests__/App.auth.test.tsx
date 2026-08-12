import { beforeEach, describe, expect, it } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import App from '../App';
import useAppStore from '../stores/appStore';

describe('App authentication boundary', () => {
  beforeEach(() => {
    localStorage.clear();
    useAppStore.setState({ currentTask: null, currentTab: 'url' });
  });

  it('switches from login to the application without changing a component hook order', async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByRole('heading', { name: 'Authentication Required' })).toBeInTheDocument();

    await user.type(screen.getByLabelText('Password'), 'test-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByRole('heading', { name: 'Repackage a Dify Plugin' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Something went wrong' })).not.toBeInTheDocument();
  });
});
