// This file is a part of the project HLab.

#include <stdio.h>

#include <Windows.h>
#include "resource.h"

static LRESULT CALLBACK WindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

// WinMain
int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, char *lpCmdLine, int nCmdShow)
{
    // printf("Hello HLab.");
    const HICON icon = LoadIcon(GetModuleHandleW(NULL), MAKEINTRESOURCEW(IDI_MAIN));

    WNDCLASSEXW wcexw = {0};
    wcexw.cbSize = sizeof(WNDCLASSEXW);
    wcexw.style = CS_DBLCLKS;
    wcexw.lpfnWndProc = (WNDPROC)WindowProc;
    wcexw.cbClsExtra = 0;
    wcexw.cbWndExtra = 0;
    wcexw.hInstance = hInstance;
    wcexw.hIcon = icon;
    wcexw.hCursor = LoadCursor(NULL, IDC_ARROW);
    wcexw.hbrBackground = NULL;
    wcexw.lpszMenuName = NULL;
    wcexw.lpszClassName = L"Heng";
    wcexw.hIconSm = icon;

    if (!RegisterClassExW(&wcexw))
    {
        MessageBoxW(NULL, L"Failed to create window.", L"Error", MB_OK);
        ExitProcess(127);
    }

    HWND hwnd = CreateWindowExW(
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
        MessageBoxW(NULL, L"Failed to create window.", L"Error", MB_OK);
        ExitProcess(127);
    }
    ShowWindow(hwnd, SW_SHOW);

    MSG msg = {0};
    while (GetMessageW(&msg, NULL, 0, 0) > 0)
    {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    return 0;
}