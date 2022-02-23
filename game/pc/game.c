// This file is a part of the project HLab.

#include <stdio.h>

#include <Windows.h>
#include "resource.h"

static int quit = 0;

static LRESULT CALLBACK WindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    if (msg == WM_DESTROY) {
        quit = 1;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

// WinMain
int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, char *lpCmdLine, int nCmdShow)
{
    // printf("Hello HLab.");
    const HICON icon = LoadIcon(GetModuleHandle(NULL), MAKEINTRESOURCEW(IDI_MAIN));

    WNDCLASSEX wcex = {0};
    wcex.cbSize = sizeof(WNDCLASSEXW);
    wcex.style = CS_DBLCLKS;
    wcex.lpfnWndProc = (WNDPROC)WindowProc;
    wcex.cbClsExtra = 0;
    wcex.cbWndExtra = 0;
    wcex.hInstance = hInstance;
    wcex.hIcon = icon;
    wcex.hCursor = LoadCursor(NULL, IDC_ARROW);
    wcex.hbrBackground = NULL;
    wcex.lpszMenuName = NULL;
    wcex.lpszClassName = L"Heng";
    wcex.hIconSm = icon;

    if (!RegisterClassEx(&wcex))
    {
        MessageBoxW(NULL, L"Failed to create window.", L"Error", MB_OK);
        ExitProcess(127);
    }

    HWND hwnd = CreateWindowEx(
        0,
        L"Heng",
        L"Hlab",
        (WS_OVERLAPPEDWINDOW | WS_CAPTION | WS_BORDER),
        0, 0, 900, 600,
        NULL,
        NULL,
        hInstance,
        NULL);

    if (!hwnd)
    {
        MessageBox(NULL, L"Failed to create window.", L"Error", MB_OK);
        ExitProcess(127);
    }
    ShowWindow(hwnd, SW_SHOW);

    // RUN
    MSG msg = {0};
    while (!quit)
    {
        while (PeekMessage(&msg, NULL, 0U, 0U, PM_REMOVE) != 0)
        {
            if (msg.message == WM_DESTROY)
            {
                PostQuitMessage(0);
                break;
            }
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
        SleepEx(0, TRUE);
    }
    return 0;
}