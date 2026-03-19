import { ref, computed } from 'vue'
import axios from 'axios'

/**
 * Composable for playbook slash-command autocomplete in chat inputs.
 *
 * Detects when the user types / at the start of a word, filters available
 * playbooks, provides ghost-text completion and dropdown navigation.
 */
export function usePlaybookAutocomplete() {
  const playbooks = ref([])

  // Autocomplete UI state
  const showDropdown = ref(false)
  const query = ref('')          // Text the user has typed after the /
  const selectedIndex = ref(0)
  const slashStart = ref(-1)     // Character index of the / that triggered autocomplete

  // Argument-hint state (shown after a completed command + space)
  const activeArgHint = ref(null) // { name, argument_hint, description }

  const filteredPlaybooks = computed(() => {
    const q = query.value.toLowerCase()
    const list = playbooks.value.filter(p => p.user_invocable !== false)
    if (!q) return list

    // Starts-with matches first, then contains
    const starts = list.filter(p => p.name.toLowerCase().startsWith(q))
    const contains = list.filter(p => !p.name.toLowerCase().startsWith(q) && p.name.toLowerCase().includes(q))
    return [...starts, ...contains]
  })

  // The trailing characters of the top suggestion that the user hasn't typed yet
  const ghostCompletion = computed(() => {
    if (!showDropdown.value || filteredPlaybooks.value.length === 0) return ''
    const top = filteredPlaybooks.value[Math.min(selectedIndex.value, filteredPlaybooks.value.length - 1)]
    if (!top) return ''
    const q = query.value
    if (top.name.toLowerCase().startsWith(q.toLowerCase())) {
      return top.name.slice(q.length)
    }
    return ''
  })

  /** Load (or refresh) playbooks for the given agent. */
  async function load(agentName, authHeader) {
    if (!agentName) return
    try {
      const response = await axios.get(`/api/agents/${agentName}/playbooks`, {
        headers: authHeader
      })
      playbooks.value = response.data.skills || []
    } catch {
      // Autocomplete is a nice-to-have – fail silently
    }
  }

  /**
   * Call on every input event.
   * Returns the current mode: 'completion' | 'argument' | 'none'
   *
   * Strategy: walk backward from the caret to find the last word-boundary slash
   * (i.e. preceded by whitespace or at position 0). Everything from that slash
   * to the caret is the "active command context".
   */
  function parse(value, caretPos) {
    const textBefore = value.slice(0, caretPos)

    // Find the last word-boundary slash before the caret
    let contextStart = -1
    for (let i = caretPos - 1; i >= 0; i--) {
      if (value[i] === '/') {
        if (i === 0 || /\s/.test(value[i - 1])) {
          contextStart = i
          break
        }
      }
      // Stop at newlines — slash commands are single-line
      if (value[i] === '\n') break
    }

    if (contextStart === -1) {
      _hide()
      activeArgHint.value = null
      return 'none'
    }

    // Context = everything after the slash up to the caret
    const context = textBefore.slice(contextStart + 1)
    const firstSpace = context.indexOf(' ')

    if (firstSpace === -1) {
      // Still typing the command name → show completion dropdown
      slashStart.value = contextStart
      query.value = context
      showDropdown.value = true
      if (selectedIndex.value >= filteredPlaybooks.value.length) {
        selectedIndex.value = 0
      }
      activeArgHint.value = null
      return 'completion'
    }

    // Command name is complete (space was typed) → show argument hint
    const commandName = context.slice(0, firstSpace)
    const matched = playbooks.value.find(p => p.name === commandName)
    _hide()
    if (matched && matched.argument_hint) {
      activeArgHint.value = matched
      return 'argument'
    }
    activeArgHint.value = null
    return 'none'
  }

  /** Accept the currently highlighted (or top) suggestion. */
  function accept(value, caretPos) {
    if (slashStart.value === -1 || filteredPlaybooks.value.length === 0) return null
    const playbook = filteredPlaybooks.value[Math.min(selectedIndex.value, filteredPlaybooks.value.length - 1)]
    return _complete(playbook, value, caretPos)
  }

  /** Accept a specific playbook (e.g. clicked from dropdown). */
  function acceptPlaybook(playbook, value, caretPos) {
    return _complete(playbook, value, caretPos)
  }

  function _complete(playbook, value, caretPos) {
    const before = value.slice(0, slashStart.value)
    const after = value.slice(caretPos)
    const newValue = before + '/' + playbook.name + ' ' + after.trimStart()
    const newCaret = before.length + playbook.name.length + 2 // after "/ + name + space"
    _hide()
    activeArgHint.value = playbook.argument_hint ? playbook : null
    return { value: newValue, caretPos: newCaret, playbook }
  }

  function _hide() {
    showDropdown.value = false
    query.value = ''
    slashStart.value = -1
    selectedIndex.value = 0
  }

  function hide() { _hide() }

  function moveDown() {
    if (filteredPlaybooks.value.length > 0) {
      selectedIndex.value = (selectedIndex.value + 1) % filteredPlaybooks.value.length
    }
  }

  function moveUp() {
    if (filteredPlaybooks.value.length > 0) {
      selectedIndex.value = (selectedIndex.value - 1 + filteredPlaybooks.value.length) % filteredPlaybooks.value.length
    }
  }

  return {
    playbooks,
    showDropdown,
    query,
    selectedIndex,
    filteredPlaybooks,
    ghostCompletion,
    activeArgHint,
    slashStart,
    load,
    parse,
    accept,
    acceptPlaybook,
    hide,
    moveDown,
    moveUp,
  }
}
