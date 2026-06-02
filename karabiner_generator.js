// JavaScript must be written in ECMAScript 5.1.
// INSTANT 19-Key Macro Pad — Karabiner complex_modifications generator
// Device: INSTANT (vendor_id: 12538 / 0x30FA, product_id: 9040 / 0x2350)

function main() {
  var DEVICE_CONDITION = {
    type: 'device_if',
    identifiers: [{ vendor_id: 12538, product_id: 9040 }]
  };

  // to_type:
  //   'shell'    → shell_command string
  //   'key'      → key_code (+ optional mods array)
  //   'consumer' → consumer_key_code (media keys)
  var keys = [
    { num: 1,  from: 'a',             to_type: 'shell',    to: "open -a 'Terminal'" },
    { num: 2,  from: 'b',             to_type: 'shell',    to: "open -a 'Visual Studio Code'" },
    { num: 3,  from: 'c',             to_type: 'shell',    to: "open -a 'Safari'" },
    { num: 4,  from: 'd',             to_type: 'key',      to: 'mission_control' },
    { num: 5,  from: 'e',             to_type: 'key',      to: 'f',        mods: ['left_command', 'left_control'] },
    { num: 6,  from: 'f',             to_type: 'key',      to: 'spacebar', mods: ['left_command'] },
    { num: 7,  from: 'g',             to_type: 'key',      to: 'z',        mods: ['left_command'] },
    { num: 8,  from: 'h',             to_type: 'key',      to: 'z',        mods: ['left_command', 'left_shift'] },
    { num: 9,  from: 'i',             to_type: 'key',      to: 'c',        mods: ['left_command'] },
    { num: 10, from: 'j',             to_type: 'key',      to: 'v',        mods: ['left_command'] },
    { num: 11, from: 'keypad_period', to_type: 'key',      to: 'x',        mods: ['left_command'] },
    { num: 12, from: 'keypad_enter',  to_type: 'shell',    to: "screencapture -i ~/Desktop/screenshot-$(date +%Y%m%d-%H%M%S).png" },
    { num: 13, from: 'keypad_hyphen', to_type: 'consumer', to: 'play_or_pause' },
    { num: 14, from: 'keypad_plus',   to_type: 'consumer', to: 'fast_forward' },
    { num: 15, from: 'spacebar',      to_type: 'consumer', to: 'rewind' },
    { num: 16, from: 'down_arrow',    to_type: 'shell',    to: "open -a 'Finder'" },
    { num: 17, from: 'left_arrow',    to_type: 'shell',    to: "open -a 'System Settings'" },
    { num: 18, from: 'right_arrow',   to_type: 'key',      to: 'tab',      mods: ['left_command'] },
    { num: 19, from: 'up_arrow',      to_type: 'key',      to: 'tab',      mods: ['left_command', 'left_shift'] }
  ];

  var manipulators = [];

  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    var toAction;

    if (k.to_type === 'shell') {
      toAction = { shell_command: k.to };
    } else if (k.to_type === 'consumer') {
      toAction = { consumer_key_code: k.to };
    } else {
      toAction = { key_code: k.to };
      if (k.mods) { toAction.modifiers = k.mods; }
    }

    console.log('Key ' + k.num + ': ' + k.from + ' → [' + k.to_type + '] ' + k.to);

    manipulators.push({
      type: 'basic',
      description: 'Key ' + k.num + ' (' + k.from + ')',
      conditions: [DEVICE_CONDITION],
      from: { key_code: k.from },
      to: [toAction]
    });
  }

  return {
    description: 'INSTANT 19-Key Macro Pad',
    manipulators: manipulators
  };
}

main();
