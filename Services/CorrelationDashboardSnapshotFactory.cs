using System.Globalization;
using TradingViewWebhookDashboard.Models;

namespace TradingViewWebhookDashboard.Services;

public static class CorrelationDashboardSnapshotFactory
{
    public static CorrelationDashboardSnapshot CreateEmpty(
        CorrelationDashboardOptions options,
        TimeZoneInfo timeZone)
    {
        var nowUtc = DateTimeOffset.UtcNow;
        return new CorrelationDashboardSnapshot
        {
            Title = options.PageTitle,
            BaseSymbol = options.BaseSymbol,
            BaseTradingViewSymbol = options.BaseTradingViewSymbol,
            MarketLabel = "Bitget USDT 永續合約",
            WindowLabel = $"{options.Granularity} x {options.GetSafeCandleLimit()} 根 K 線",
            CorrelationRangeLabel = $"{options.MinCorrelation:0.00} ~ {options.MaxCorrelation:0.00}",
            RefreshIntervalMinutes = (int)options.GetRefreshInterval().TotalMinutes,
            UpdatedAtUtc = nowUtc.ToString("O"),
            UpdatedAtLocalText = "等待第一次更新",
            LastSuccessfulRefreshLocalText = "尚未成功更新",
            NextScheduledRefreshLocalText = FormatLocal(nowUtc + options.GetRefreshInterval(), timeZone),
            BtcDirection = "flat",
            BtcDirectionLabel = $"等待 {options.BaseTradingViewSymbol} 最新日 K 方向",
            BasePriceChangePercent = 0m,
            BasePriceChangeText = "0.00%",
            BaseLastClose = 0m,
            BaseLastCloseText = "-",
            TotalSymbolsScanned = 0,
            MatchedCount = 0,
            DirectionRuleText = $"資料更新後會顯示和 {options.BaseTradingViewSymbol} 最新日 K 同方向、且相關係數介於 {options.MinCorrelation:0.00} 到 {options.MaxCorrelation:0.00} 的標的。",
            Results = []
        };
    }

    public static CorrelationDashboardSnapshot CreateSuccess(
        CorrelationDashboardOptions options,
        TimeZoneInfo timeZone,
        DateTimeOffset generatedAtUtc,
        decimal baseLastClose,
        decimal basePriceChangePercent,
        string btcDirection,
        string btcDirectionLabel,
        string directionRuleText,
        int totalSymbolsScanned,
        IReadOnlyList<CorrelationCoinResult> results)
    {
        return new CorrelationDashboardSnapshot
        {
            Title = options.PageTitle,
            BaseSymbol = options.BaseSymbol,
            BaseTradingViewSymbol = options.BaseTradingViewSymbol,
            MarketLabel = "Bitget USDT 永續合約",
            WindowLabel = $"{options.Granularity} x {options.GetSafeCandleLimit()} 根 K 線",
            CorrelationRangeLabel = $"{options.MinCorrelation:0.00} ~ {options.MaxCorrelation:0.00}",
            RefreshIntervalMinutes = (int)options.GetRefreshInterval().TotalMinutes,
            UpdatedAtUtc = generatedAtUtc.ToString("O"),
            UpdatedAtLocalText = FormatLocal(generatedAtUtc, timeZone),
            LastSuccessfulRefreshUtc = generatedAtUtc.ToString("O"),
            LastSuccessfulRefreshLocalText = FormatLocal(generatedAtUtc, timeZone),
            NextScheduledRefreshLocalText = FormatLocal(generatedAtUtc + options.GetRefreshInterval(), timeZone),
            BtcDirection = btcDirection,
            BtcDirectionLabel = btcDirectionLabel,
            BasePriceChangePercent = basePriceChangePercent,
            BasePriceChangeText = FormatPercent(basePriceChangePercent),
            BaseLastClose = baseLastClose,
            BaseLastCloseText = baseLastClose.ToString("0.########", CultureInfo.InvariantCulture),
            TotalSymbolsScanned = totalSymbolsScanned,
            MatchedCount = results.Count,
            DirectionRuleText = directionRuleText,
            Results = results
        };
    }

    public static CorrelationDashboardSnapshot CreateRefreshFailure(
        CorrelationDashboardSnapshot previous,
        CorrelationDashboardOptions options,
        TimeZoneInfo timeZone,
        DateTimeOffset attemptedAtUtc,
        string errorMessage)
    {
        return previous with
        {
            Title = options.PageTitle,
            UpdatedAtUtc = attemptedAtUtc.ToString("O"),
            UpdatedAtLocalText = FormatLocal(attemptedAtUtc, timeZone),
            NextScheduledRefreshLocalText = FormatLocal(attemptedAtUtc + options.GetRefreshInterval(), timeZone),
            ErrorMessage = errorMessage
        };
    }

    private static string FormatLocal(DateTimeOffset timestamp, TimeZoneInfo timeZone)
    {
        var local = TimeZoneInfo.ConvertTime(timestamp, timeZone);
        return local.ToString("yyyy-MM-dd HH:mm:ss");
    }

    private static string FormatPercent(decimal value)
    {
        return value switch
        {
            > 0m => $"+{value:0.00}%",
            < 0m => $"{value:0.00}%",
            _ => "0.00%"
        };
    }
}
