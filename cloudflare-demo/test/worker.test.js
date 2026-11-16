import test from "node:test";
import assert from "node:assert/strict";
import worker, { buildPrompt, buildRetryPrompt, validateInput, validateOutput } from "../src/index.js";


async function runWorkerWithOutputs(context, outputs) {
  const prompts = [];
  const env = {
    ROAST_LIMITER: { limit: async () => ({ success: true }) },
    AI: {
      run: async (_model, options) => {
        prompts.push(options.messages[1].content);
        const index = Math.min(prompts.length - 1, outputs.length - 1);
        return { response: outputs[index] };
      }
    }
  };
  const request = new Request("https://cooked.test/api/roast", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text: context, style: "instagram", intensity: 3 })
  });
  const response = await worker.fetch(request, env);
  return { response, prompts };
}

const valid = {
  text: "He said he was taking a break from his phone, then replied to every comment within seconds.",
  style: "instagram",
  intensity: 3
};

test("accepts a valid setup and style", () => {
  assert.equal(validateInput(valid), null);
});

test("rejects missing, oversized and unsupported requests", () => {
  assert.match(validateInput(null), /valid comment setup/i);
  assert.match(validateInput({ ...valid, text: "x" }), /between 3 and 600/i);
  assert.match(validateInput({ ...valid, text: "x".repeat(601) }), /between 3 and 600/i);
  assert.match(validateInput({ ...valid, style: "mean" }), /four available styles/i);
  assert.match(validateInput({ ...valid, intensity: 6 }), /between 1 and 5/i);
});

test("rejects email addresses and phone numbers in setups", () => {
  assert.match(validateInput({ ...valid, text: "Email me at test@example.com please." }), /remove phone numbers or email/i);
  assert.match(validateInput({ ...valid, text: "Call me at +1 202 555 0147 today." }), /remove phone numbers or email/i);
});

test("rejects explicit targeted harassment requests", () => {
  assert.match(
    validateInput({ ...valid, text: "Roast him for his appearance and weight." }),
    /targets situations and choices/i
  );
});

test("prompt preserves the selected style, situation and spice level", () => {
  const prompt = buildPrompt(valid.text, "instagram", 4);
  assert.match(prompt, /taking a break from his phone/i);
  assert.match(prompt, /Instagram-comment energy/i);
  assert.match(prompt, /4\/5/);
  assert.match(prompt, /Return only the comment/i);
});

test("retry prompt makes relevance clearer without changing the setup", () => {
  const prompt = buildRetryPrompt("He eats alot.", "instagram", 3);
  assert.ok(prompt.includes("He eats alot."));
  assert.ok(prompt.includes("previous attempt did not pass"));
  assert.ok(prompt.includes("concrete word or close synonym"));
});

test("accepts a context-grounded, safe comment", () => {
  assert.equal(
    validateOutput("The refresh button won't let him unplug.", valid.text),
    true
  );
});

test("accepts relevant comments for short, broad setups", () => {
  assert.equal(validateOutput("Fridge gets him.", "He eats alot."), true);
  assert.equal(validateOutput("The silence has started charging him rent.", "He talks alot."), true);
});

test("still rejects unrelated comments for short setups", () => {
  assert.equal(validateOutput("The airport has updated its opening hours.", "He eats alot."), false);
});

test("rejects an unrelated, unsafe or overlong comment", () => {
  assert.equal(validateOutput("The airport has entered the chat today.", valid.text), false);
  assert.equal(validateOutput("The refresh button gave everyone insomnia.", valid.text), false);
  assert.equal(validateOutput("The refresh button says hurt yourself right now.", valid.text), false);
  assert.equal(validateOutput("refresh ".repeat(30), valid.text), false);
});


test("request handler retries once when the first comment fails relevance", async () => {
  const { response, prompts } = await runWorkerWithOutputs(
    "He eats alot.",
    ["The airport opens at dawn today.", "Fridge gets him."]
  );
  assert.equal(response.status, 200);
  assert.equal((await response.json()).roast, "Fridge gets him.");
  assert.equal(prompts.length, 2);
  assert.match(prompts[1], /RETRY:/);
});

test("request handler skips the retry when the first comment passes", async () => {
  const { response, prompts } = await runWorkerWithOutputs(
    "He eats alot.",
    ["Fridge gets him."]
  );
  assert.equal(response.status, 200);
  assert.equal(prompts.length, 1);
});

test("request handler returns the existing error when both attempts fail", async () => {
  const { response, prompts } = await runWorkerWithOutputs(
    "He eats alot.",
    ["The airport opens at dawn today.", "A completely unrelated weather report."]
  );
  assert.equal(response.status, 503);
  assert.equal(prompts.length, 2);
});
