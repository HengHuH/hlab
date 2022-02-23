// This file is a part of the project HLab.

#include <stdio.h>

#include <Windows.h>

// WinMain
int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, char *lpCmdLine, int nCmdShow)
{
    printf("Hello HLab.");
    MessageBoxW(NULL, L"Hello", L"Error", MB_OK);
    return 0;
}