using Launcher.App.Navigation;

namespace Launcher.App.Ui;

/// <summary>The controls' hints several screens share (<see cref="HintBar"/>), kept once.</summary>
public static class CommonHints
{
    public static readonly Hint[] Back = [new("Back", Prompt.Back)];

    public static readonly Hint[] ChooseBack = [new("Choose", Prompt.Accept), new("Back", Prompt.Back)];

    public static readonly Hint[] ChangeBack = [new("Change", Prompt.Accept), new("Back", Prompt.Back)];

    public static readonly Hint[] ChooseChangeBack = [new("Choose", Prompt.Accept), new("Change", Prompt.LeftRight), new("Back", Prompt.Back)];

    public static readonly Hint[] ChooseRemoveBack = [new("Choose", Prompt.Accept), new("Remove", Prompt.Secondary), new("Back", Prompt.Back)];
}
