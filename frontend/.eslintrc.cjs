// 项目级 ESLint 覆盖（frontend workspace 根，向上级联覆盖用户全局 Vue2 规则集）。
// 目的：`v-model:value` 是 Vue3 + naive-ui 标准语法；`<template v-for :key>` 与模板内
// 表达式断言在 Vue3 均合法——这些均非真实错误，仅为旧版规则集的误报，此处显式关闭。
module.exports = {
  rules: {
    "vue/no-v-model-argument": "off",
    "vue/no-v-for-template-key": "off",
    "vue/no-parsing-error": "off",
    "vue/multi-word-component-names": "off",
  },
}
