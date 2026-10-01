using System;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Platform;

namespace Launcher.App.Screens;

/// <summary>
/// View (Select) or P in the grids: restart, shut down or sleep the system, or quit the launcher. A row acts at once
/// (opening the menu is the confirmation); B, Escape or View again closes it. What the system can't do here is
/// dimmed, saying why. The request runs on a worker, since sleep returns only once the computer wakes. A restart or
/// shutdown the system accepted quits the launcher, so its databases are closed before Windows ends it.
/// </summary>
public sealed partial class PowerMenu : ListPanel
{
    private readonly IPowerControl _power;
    private readonly MainThreadQueue _queue;
    private readonly Action _quit;

    public PowerMenu(IPowerControl power, MainThreadQueue queue, Action quit)
        : base("Power", new Vector2(720, 400), dimBelow: true)
    {
        _power = power;
        _queue = queue;
        _quit = quit;
        AddAction(PowerAction.Restart, "Restart system", "Close every app and restart the computer");
        AddAction(PowerAction.ShutDown, "Shut down system", "Close every app and turn the computer off");
        AddAction(PowerAction.Sleep, "Sleep system", "The launcher is here as you left it when the computer wakes");
        AddRow("Quit app", "Close Odyssey Launcher and go back to the desktop", activated: () =>
        {
            GD.Print("Power: quitting the app.");
            Close();
            _quit();
        });
        SetHints("A  Choose     B / View  Cancel");
    }

    protected override string BackLabel => "Cancel";

    public override bool Handle(NavCommand command)
    {
        if (command != NavCommand.Power)
        {
            return false;
        }

        Close();
        return true;
    }

    private void AddAction(PowerAction action, string title, string detail)
    {
        var unavailable = _power.Unavailable(action);
        var row = AddRow(title, unavailable ?? detail, activated: () => Request(action));
        row.Disabled = unavailable is not null;
    }

    private void Request(PowerAction action)
    {
        var layer = Layer;
        var (power, queue, quit) = (_power, _queue, _quit);
        Close();
        GD.Print($"Power: asking the system to {action}.");
        _ = Task.Run(() =>
        {
            string? problem;
            try
            {
                problem = power.Request(action);
            }
            catch (Exception e)
            {
                problem = e.Message;
            }

            queue.Post(() =>
            {
                if (problem is not null)
                {
                    GD.PushWarning($"Power: {problem}");
                    ConfirmDialog.Tell(layer, action switch
                    {
                        PowerAction.Restart => "Couldn't restart",
                        PowerAction.ShutDown => "Couldn't shut down",
                        _ => "Couldn't sleep",
                    }, problem);
                }
                else if (action != PowerAction.Sleep)
                {
                    GD.Print($"Power: the system accepted {action}, so the app quits.");
                    quit();
                }
            });
        });
    }
}
