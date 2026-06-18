IF DB_ID('TimesheetDB') IS NULL
    CREATE DATABASE [TimesheetDB];
GO

USE [TimesheetDB];
GO

-- ============================================================
-- Подразделения / Рестораны
-- ============================================================
IF OBJECT_ID('dbo.ПодразделенияОрганизаций', 'U') IS NULL
CREATE TABLE [dbo].[ПодразделенияОрганизаций] (
    [Ссылка]        NVARCHAR(36)  NOT NULL,
    [Наименование]  NVARCHAR(255) NOT NULL,
    CONSTRAINT [PK_ПодразделенияОрганизаций] PRIMARY KEY CLUSTERED ([Ссылка])
);
GO

-- ============================================================
-- Должности
-- ============================================================
IF OBJECT_ID('dbo.ДолжностиОрганизаций', 'U') IS NULL
CREATE TABLE [dbo].[ДолжностиОрганизаций] (
    [Ссылка]        NVARCHAR(36)  NOT NULL,
    [Наименование]  NVARCHAR(255) NOT NULL,
    CONSTRAINT [PK_ДолжностиОрганизаций] PRIMARY KEY CLUSTERED ([Ссылка])
);
GO

-- ============================================================
-- Сотрудники
-- ============================================================
IF OBJECT_ID('dbo.СотрудникиОрганизаций_Перевод', 'U') IS NULL
CREATE TABLE [dbo].[СотрудникиОрганизаций_Перевод] (
    [Ссылка]                              NVARCHAR(36)  NOT NULL,
    [Наименование]                        NVARCHAR(255) NOT NULL,
    [ДатаПриемаНаРаботу]                  NVARCHAR(10)      NULL,
    [ДатаУвольнения]                      NVARCHAR(10)      NULL,
    [ТекущаяДолжностьОрганизации]         NVARCHAR(36)      NULL,
    [ТекущееПодразделениеОрганизации]     NVARCHAR(36)      NULL,

    CONSTRAINT [PK_СотрудникиОрганизаций_Перевод] PRIMARY KEY CLUSTERED ([Ссылка]),

    CONSTRAINT [FK_Сотрудники_Должность]
        FOREIGN KEY ([ТекущаяДолжностьОрганизации])
        REFERENCES [dbo].[ДолжностиОрганизаций] ([Ссылка]),

    CONSTRAINT [FK_Сотрудники_Подразделение]
        FOREIGN KEY ([ТекущееПодразделениеОрганизации])
        REFERENCES [dbo].[ПодразделенияОрганизаций] ([Ссылка])
);
GO

-- ============================================================
-- Табель (таблица фактов)
-- ============================================================
IF OBJECT_ID('dbo.ТабельОрганизаций', 'U') IS NULL
CREATE TABLE [dbo].[ТабельОрганизаций] (
    [id]                 NVARCHAR(50)  NOT NULL,
    [date]               DATE          NOT NULL,
    [restaurant_id]      NVARCHAR(36)  NOT NULL,
    [employee_id]        NVARCHAR(36)  NOT NULL,
    [position_id]        NVARCHAR(36)      NULL,
    [target_position_id] NVARCHAR(36)      NULL,
    [hours]              DECIMAL(5,2)      NULL,
    [work_type]          NVARCHAR(20)      NULL,
    [is_correction]      BIT           NOT NULL DEFAULT 0,
    [comment]            NVARCHAR(500)     NULL,
    [created_at]         DATETIME2     NOT NULL DEFAULT GETDATE(),
    [is_vacation]        BIT           NOT NULL DEFAULT 0,
    [is_sick]            BIT           NOT NULL DEFAULT 0,
    [is_without_pay]     BIT           NOT NULL DEFAULT 0,

    CONSTRAINT [PK_ТабельОрганизаций] PRIMARY KEY CLUSTERED ([id]),

    CONSTRAINT [FK_Табель_Подразделение]
        FOREIGN KEY ([restaurant_id])
        REFERENCES [dbo].[ПодразделенияОрганизаций] ([Ссылка]),

    CONSTRAINT [FK_Табель_Сотрудник]
        FOREIGN KEY ([employee_id])
        REFERENCES [dbo].[СотрудникиОрганизаций_Перевод] ([Ссылка]),

    CONSTRAINT [FK_Табель_Должность]
        FOREIGN KEY ([position_id])
        REFERENCES [dbo].[ДолжностиОрганизаций] ([Ссылка]),

    CONSTRAINT [FK_Табель_ЦелеваяДолжность]
        FOREIGN KEY ([target_position_id])
        REFERENCES [dbo].[ДолжностиОрганизаций] ([Ссылка])
);
GO

-- ============================================================
-- Индексы
-- ============================================================
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Табель_date_restaurant')
CREATE NONCLUSTERED INDEX [IX_Табель_date_restaurant]
    ON [dbo].[ТабельОрганизаций] ([date], [restaurant_id]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Табель_employee_date')
CREATE NONCLUSTERED INDEX [IX_Табель_employee_date]
    ON [dbo].[ТабельОрганизаций] ([employee_id], [date], [work_type])
    INCLUDE ([position_id], [target_position_id], [created_at], [is_correction], [id]);
GO
